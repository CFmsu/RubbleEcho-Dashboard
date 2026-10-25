"""Grid plan for the sand table.

A photo note, or the table geometry when no frame is stored, produces a virtual
boundary and an order of the six measurement points. The ultrasonic sample can
block a cell and rotate the planned look. A detected signal paints the heatmap
at the camera pose when that pose is valid, otherwise at the cell. No plan
writes a motor, a pin, or a speed.
"""

from __future__ import annotations

import json

from app.ai.validators import _reject_forbidden
from app.config.geometry import load_geometry, point_map, traversable_bounds
from app.config.settings import ULTRASONIC_CAUTION_CM, ULTRASONIC_STOP_CM, ai_enabled
from app.services.clock import utc_now

LOOKS = ("forward", "left", "right")
SIGNAL_CLASSES = {"knock", "scratch", "scratch/scrape", "periodic_tapping"}


def plan_from_photo() -> dict:
    from app.ai.nebius_client import ai_status, plan_live, vision_live
    from app.config.settings import nebius_vision_model
    from app.state import get_state

    state = get_state()
    photo = _photo_note(state)
    frame = _frame_bytes(state)
    vision_note = "No camera frame was stored, so the vision model was not called. "
    if frame is not None and nebius_vision_model():
        image, mime = frame
        seen = vision_live(image, mime, str(photo.get("note") or ""))
        if seen.get("ok"):
            photo["scene"] = seen["scene"]
            photo["frame"] = "described"
            state.scene_note = seen["scene"]
            vision_note = "Vision described the stored frame. "
        else:
            photo["vision_error"] = seen.get("kind")
            vision_note = f"Vision did not describe the frame ({seen.get('kind')}). "
    local = _local_plan(photo)
    status = ai_status()
    if status["status"] == "NOT_CONFIGURED" or not ai_enabled():
        return _store(state, local, "Grid plan uses the table inset. The model is not configured, so no Token Factory call was made.")
    live = plan_live(photo, [cell["point_id"] for cell in local["cells"]])
    if not live.get("ok"):
        local["model_error"] = live.get("kind")
        return _store(state, local, f"{vision_note}Model plan failed ({live.get('kind')}). The table inset is in use.")
    parsed, reason = _accept_model_plan(live.get("text") or "", local)
    if parsed is None:
        local["model_error"] = reason
        return _store(state, local, f"{vision_note}The model plan was rejected ({reason}). The table inset is in use.")
    parsed["model_id"] = live.get("model_id")
    if parsed.get("boundary_replaced"):
        note = vision_note + "Grid plan accepted from the model. Its boundary was outside the table, so the traversable inset is the virtual line. Motors were not commanded."
    else:
        note = vision_note + "Grid plan accepted from the model. Motors were not commanded."
    return _store(state, parsed, note)


def apply_obstacle() -> dict:
    from app.state import get_state

    state = get_state()
    if state.search_plan is None:
        plan_from_photo()
    plan = state.search_plan
    sample = state.ultrasonic or {}
    distance = sample.get("distance_cm")
    timeout = bool(sample.get("echo_timeout", True)) if state.ultrasonic else True
    if state.ultrasonic is None:
        return {"ok": False, "message": "No ultrasonic sample yet. The grid was not changed.", "plan": plan}
    if timeout or distance is None or distance < ULTRASONIC_STOP_CM:
        blocked = _block_next(plan)
        plan["look"] = _rotate(plan.get("look") or "forward")
        plan["path"] = _open_path(plan)
        note = (
            f"Ultrasonic {distance if distance is not None else 'timeout'} cm blocked {blocked or 'no open cell'}. "
            f"Planned look is now {plan['look']}. The camera and ultrasonic facing are planned only."
        )
        plan["obstacle"] = {"distance_cm": distance, "blocked_point_id": blocked, "look": plan["look"]}
        return _store(state, plan, note)
    if distance < ULTRASONIC_CAUTION_CM:
        plan["obstacle"] = {"distance_cm": distance, "blocked_point_id": None, "look": plan.get("look")}
        return _store(state, plan, f"Ultrasonic {distance} cm is inside the caution margin. The path is unchanged.")
    plan["obstacle"] = {"distance_cm": distance, "blocked_point_id": None, "look": plan.get("look")}
    return _store(state, plan, f"Ultrasonic {distance} cm is clear of the stop margin. The path is unchanged.")


def apply_signal() -> dict:
    from app.services.mission import request_reason
    from app.state import get_state

    state = get_state()
    if state.search_plan is None:
        plan_from_photo()
    plan = state.search_plan
    kind = _signal_kind(state)
    if kind is None:
        reasoned = request_reason()
        return {
            "ok": True,
            "message": "No knock, scratch, or radar presence in the latest sample. The heatmap was not changed.",
            "plan": plan,
            "reasoning": reasoned.get("reasoning"),
        }
    cell = _take_current(plan)
    point = _heatmap_point(state, cell, kind)
    if cell is not None:
        state.heatmap = [item for item in state.heatmap if item["point_id"] != cell["point_id"]]
        state.heatmap.append(point)
    plan["path"] = _open_path(plan)
    _store(state, plan, f"Signal {kind} recorded at {point['point_id']}.")
    reasoned = request_reason()
    return {
        "ok": True,
        "message": f"Signal {kind} painted on the heatmap at {point['x_cm']}, {point['y_cm']} cm. The model was asked where to listen next.",
        "plan": state.search_plan,
        "heatmap_point": point,
        "reasoning": reasoned.get("reasoning"),
    }


def _store(state, plan: dict, message: str) -> dict:
    plan["updated_at_utc"] = utc_now()
    plan["execute_hardware"] = False
    state.search_plan = plan
    state.add_event(
        device="search_plan",
        sensor="grid",
        summary=message,
        quality=plan.get("source") or "local_grid",
        captured_at_utc=plan["updated_at_utc"],
        value=len(plan.get("path") or []),
        unit="cells",
    )
    return {"ok": True, "message": message, "plan": plan}


def _frame_bytes(state) -> tuple[bytes, str] | None:
    from pathlib import Path

    from app.persistence.store import data_dir

    raw = getattr(state, "media_camera", None)
    if not raw:
        return None
    path = Path(str(raw)).resolve()
    root = (data_dir() / "sim_media").resolve()
    if root not in path.parents or not path.is_file():
        return None
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        return None
    data = path.read_bytes()
    if not data or len(data) > 2_000_000:
        return None
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return data, mime


def _photo_note(state) -> dict:
    camera = next((item for item in state.cameras if item["camera_id"] == "camera_top"), None)
    open_camera = bool(camera and camera.get("state") == "connected")
    return {
        "camera_id": "camera_top",
        "frame": "not_stored",
        "camera_open": open_camera,
        "note": (
            "The top camera is open, and no frame bytes were stored with this request."
            if open_camera
            else "No camera frame is available. Use the traversable inset as the virtual line."
        ),
    }


def _local_plan(photo: dict) -> dict:
    geometry = load_geometry()
    points = geometry["measurement_points"]
    order = _snake([dict(point) for point in points])
    bounds = traversable_bounds(geometry)
    cells = [
        {
            "point_id": point["id"],
            "x_cm": point["x_cm"],
            "y_cm": point["y_cm"],
            "state": "open",
        }
        for point in order
    ]
    return {
        "source": "local_grid",
        "camera_frame": photo["frame"],
        "execute_hardware": False,
        "look": "forward",
        "boundary": _rectangle(bounds),
        "cells": cells,
        "path": [cell["point_id"] for cell in cells],
        "ultrasonic": {
            "role": "guard_the_virtual_line",
            "stop_cm": ULTRASONIC_STOP_CM,
            "caution_cm": ULTRASONIC_CAUTION_CM,
            "commanded_pin": None,
        },
        "model_error": None,
        "obstacle": None,
    }


def _rectangle(bounds: dict) -> list[dict]:
    corners = [
        (bounds["min_x"], bounds["min_y"]),
        (bounds["max_x"], bounds["min_y"]),
        (bounds["max_x"], bounds["max_y"]),
        (bounds["min_x"], bounds["max_y"]),
    ]
    lines = []
    for index, start in enumerate(corners):
        end = corners[(index + 1) % len(corners)]
        lines.append({"x1_cm": start[0], "y1_cm": start[1], "x2_cm": end[0], "y2_cm": end[1]})
    return lines


def _snake(points: list[dict]) -> list[dict]:
    rows: dict[int, list[dict]] = {}
    for point in points:
        key = int(round(point["y_cm"] / 15.0))
        rows.setdefault(key, []).append(point)
    ordered = []
    for index, key in enumerate(sorted(rows)):
        row = sorted(rows[key], key=lambda item: item["x_cm"])
        if index % 2 == 1:
            row.reverse()
        ordered.extend(row)
    return ordered


def _accept_model_plan(text: str, local: dict) -> tuple[dict | None, str]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None, "no_json"
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(payload, dict):
        return None, "invalid_json"
    try:
        _reject_forbidden(payload)
    except ValueError as exc:
        return None, str(exc)
    known = {cell["point_id"] for cell in local["cells"]}
    path = payload.get("path")
    look = str(payload.get("look") or "").strip().lower()
    boundary = [_line(item) for item in payload.get("boundary") or []]
    if not isinstance(path, list) or not path:
        return None, "path"
    cleaned = []
    for item in path:
        if not isinstance(item, str) or item.strip() not in known or item.strip() in cleaned:
            return None, "path"
        cleaned.append(item.strip())
    if look not in LOOKS:
        return None, "look"
    replaced = not boundary or not _boundary_inside(boundary)
    if replaced:
        boundary = local["boundary"]
    plan = dict(local)
    plan["source"] = "nebius_token_factory"
    plan["look"] = look
    plan["boundary"] = boundary
    plan["path"] = [item for item in cleaned if _cell_state(plan, item) == "open"]
    plan["summary"] = payload.get("summary") if isinstance(payload.get("summary"), str) else ""
    plan["boundary_replaced"] = replaced
    return plan, ""


def _line(item: object) -> dict:
    if not isinstance(item, dict):
        return {}
    pairs = (("x1_cm", "x1"), ("y1_cm", "y1"), ("x2_cm", "x2"), ("y2_cm", "y2"))
    line = {}
    for canonical, alias in pairs:
        value = item.get(canonical, item.get(alias))
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                value = None
        line[canonical] = value
    return line


def _boundary_inside(boundary: list) -> bool:
    outer = load_geometry()["outer_cm"]
    for line in boundary:
        if not isinstance(line, dict):
            return False
        for key in ("x1_cm", "y1_cm", "x2_cm", "y2_cm"):
            value = line.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return False
        if not (0 <= line["x1_cm"] <= outer["width"] and 0 <= line["x2_cm"] <= outer["width"]):
            return False
        if not (0 <= line["y1_cm"] <= outer["height"] and 0 <= line["y2_cm"] <= outer["height"]):
            return False
    return True


def _block_next(plan: dict) -> str | None:
    for point_id in plan.get("path") or []:
        for cell in plan["cells"]:
            if cell["point_id"] == point_id and cell["state"] == "open":
                cell["state"] = "blocked"
                return point_id
    return None


def _take_current(plan: dict) -> dict | None:
    for point_id in plan.get("path") or []:
        for cell in plan["cells"]:
            if cell["point_id"] == point_id and cell["state"] == "open":
                cell["state"] = "signal"
                return cell
    return None


def _open_path(plan: dict) -> list[str]:
    blocked = {cell["point_id"] for cell in plan["cells"] if cell["state"] != "open"}
    return [point_id for point_id in plan.get("path") or [] if point_id not in blocked]


def _rotate(look: str) -> str:
    if look not in LOOKS:
        return "left"
    return LOOKS[(LOOKS.index(look) + 1) % len(LOOKS)]


def _cell_state(plan: dict, point_id: str) -> str:
    for cell in plan["cells"]:
        if cell["point_id"] == point_id:
            return cell["state"]
    return "open"


def _signal_kind(state) -> str | None:
    acoustic = state.acoustic or {}
    if acoustic.get("class") in SIGNAL_CLASSES:
        return str(acoustic["class"])
    radar = state.radar or {}
    if radar.get("human_presence") is True:
        return "radar_presence"
    return None


def _heatmap_point(state, cell: dict | None, kind: str) -> dict:
    pose = state.pose or {}
    use_pose = bool(pose.get("valid") and pose.get("x_cm") is not None and pose.get("y_cm") is not None)
    point_id = cell["point_id"] if cell else "camera_fix"
    if cell is None:
        known = point_map()
        point_id = next(iter(known))
        cell = {"x_cm": known[point_id]["x_cm"], "y_cm": known[point_id]["y_cm"], "point_id": point_id}
    event = state.add_event(
        device="camera_top" if use_pose else "search_plan",
        sensor="heatmap",
        summary=f"Heatmap at {'camera pose' if use_pose else point_id} after {kind}.",
        quality="sensor",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
        site_id=point_id,
    )
    return {
        "point_id": point_id,
        "x_cm": pose["x_cm"] if use_pose else cell["x_cm"],
        "y_cm": pose["y_cm"] if use_pose else cell["y_cm"],
        "score": 1.0 if kind in {"knock", "radar_presence"} else 0.6,
        "score_semantics": "uncalibrated_heuristic",
        "interpolated": False,
        "sample_count": 1,
        "method": "signal_at_camera_pose" if use_pose else "signal_at_grid_cell",
        "source_mode": "live" if use_pose or (state.radar or {}).get("source_mode") == "live" else "simulation",
        "quality": "sensor",
        "evidence_event_ids": [event["event_id"]],
    }
