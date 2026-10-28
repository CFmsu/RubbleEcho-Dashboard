"""One listen per grid square. Telemetry fills the heatmap. Photos stay with that square."""

from __future__ import annotations

import os
import threading

from app.services.clock import utc_now
from app.state import get_state

_PLACES = {"1": "first", "2": "second", "3": "third"}
_lock = threading.Lock()
_active: str | None = None
_frames: dict[str, list[bytes]] = {}
_opencv: dict[str, list[dict]] = {}
_vision: dict[str, list[str]] = {}


def place_name(cell_id: str) -> str:
    text = str(cell_id)
    if len(text) == 4 and text[0] == "r" and text[2] == "c" and text[1] in _PLACES and text[3] in _PLACES:
        return f"row {text[1]}, the {_PLACES[text[3]]} square"
    return text


def begin_run() -> None:
    global _active
    with _lock:
        _active = None
        _frames.clear()
        _opencv.clear()
        _vision.clear()


def watch(cell_id: str) -> None:
    """Keep arriving photos with this square before the listen is written down."""
    global _active
    with _lock:
        _active = cell_id
        _frames.setdefault(cell_id, [])
        _opencv.setdefault(cell_id, [])


def note_hold(cell: dict) -> None:
    """Record the sensors already in hand for this square. The motors are already stopped."""
    cell_id = str(cell.get("id") or "")
    if place_name(cell_id) == cell_id and not cell_id.startswith("r"):
        return
    if len(cell_id) != 4 or cell_id[0] != "r":
        return
    global _active
    with _lock:
        _active = cell_id
        _frames.setdefault(cell_id, [])
        _opencv.setdefault(cell_id, [])
    state = get_state()
    acoustic = state.acoustic or {}
    radar = state.radar or {}
    ultrasonic = state.ultrasonic or {}
    from app.services.briefing import sound_category
    from app.services.sim_run import _reading_score

    label = acoustic.get("class")
    category = acoustic.get("sound_category") or sound_category(label if isinstance(label, str) else None)
    previous = next((item for item in state.heatmap if item.get("point_id") == cell_id), None)
    previous_readings = previous.get("readings") if isinstance(previous, dict) and isinstance(previous.get("readings"), dict) else {}
    score = _reading_score(acoustic or None, radar or None)
    event = state.add_event(
        device="raspberry_pi_4",
        sensor="acoustic",
        summary=f"Processed sound at {place_name(cell_id)}: {category}.",
        quality="live",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
        site_id=cell_id,
        acoustic_class=label if isinstance(label, str) else None,
    )
    state.heatmap = [item for item in state.heatmap if item.get("point_id") != cell_id]
    state.heatmap.append(
        {
            "point_id": cell_id,
            "x_cm": cell.get("x_cm"),
            "y_cm": cell.get("y_cm"),
            "score": score,
            "score_semantics": "uncalibrated_from_cell_readings",
            "readings": {
                "place": place_name(cell_id),
                "sound": label,
                "sound_category": category,
                "radar_presence": radar.get("human_presence"),
                "distance_m": radar.get("distance_m"),
                "ultrasonic_cm": ultrasonic.get("distance_cm"),
                "photos": previous_readings.get("photos") or 0,
                "opencv": list(previous_readings.get("opencv") or []),
            },
            "interpolated": False,
            "sample_count": 1,
            "method": "cell_readings",
            "source_mode": "live",
            "quality": "measured",
            "evidence_event_ids": [event["event_id"]],
        }
    )


def keep_frame(raw: bytes) -> int:
    """Keep up to three Raspberry Pi frames for the square the rover is listening in."""
    if not raw:
        return 0
    with _lock:
        cell_id = _active
        if not cell_id:
            return 0
        stored = _frames.setdefault(cell_id, [])
        if len(stored) >= 3:
            return 3
        stored.append(bytes(raw))
        notes = _opencv.setdefault(cell_id, [])
        notes.append(describe_jpeg(raw))
        count = len(stored)
        saved_notes = list(notes)
    _stamp_photos(cell_id, count, saved_notes)
    return count


def describe_jpeg(raw: bytes) -> dict:
    """Brightness and edges only. OpenCV does not name what is in the frame."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return {"opencv": "not_installed", "note": "OpenCV is not installed, so this frame was stored without a measurement."}
    array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        return {"opencv": "unreadable", "note": "The frame was not a readable picture."}
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 160)
    brightness = round(float(gray.mean()), 1)
    density = round(float(edges.mean()) / 255.0, 3)
    return {
        "width": int(image.shape[1]),
        "height": int(image.shape[0]),
        "brightness": brightness,
        "edge_density": density,
        "note": f"OpenCV measured brightness {brightness} and edge density {density}. It did not name an object.",
    }


def photo_notes() -> dict[str, dict]:
    with _lock:
        return {
            cell_id: {
                "place": place_name(cell_id),
                "photos": len(_frames.get(cell_id, [])),
                "opencv": list(_opencv.get(cell_id, [])),
                "vision": list(_vision.get(cell_id, [])),
            }
            for cell_id in _frames
        }


def finish_run() -> None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        _write_result(False)
        return
    threading.Thread(target=_write_result, args=(True,), name="cell-briefing", daemon=True).start()


def _stamp_photos(cell_id: str, count: int, notes: list[dict]) -> None:
    state = get_state()
    for point in state.heatmap:
        if point.get("point_id") == cell_id and isinstance(point.get("readings"), dict):
            point["readings"]["photos"] = count
            point["readings"]["opencv"] = [item.get("note") for item in notes]


def _write_result(use_vision: bool) -> None:
    if use_vision:
        _ask_vision()
    from app.services.fusion import local_assessment
    from app.services.mission import _spoken, request_reason

    state = get_state()
    if use_vision:
        request_reason()
        return
    state.reasoning = _spoken(local_assessment(state.events, state.heatmap))


def _ask_vision() -> None:
    from app.ai.nebius_client import vision_live

    with _lock:
        pending = [(cell_id, list(frames)) for cell_id, frames in _frames.items() if frames]
    for cell_id, frames in pending:
        lines: list[str] = []
        for index, frame in enumerate(frames[:3], start=1):
            seen = vision_live(
                frame,
                "image/jpeg",
                f"Photo {index} of 3 at {place_name(cell_id)}. Describe only what is visible. Do not command the rover.",
            )
            scene = seen.get("scene") if isinstance(seen, dict) else None
            if isinstance(scene, dict) and scene.get("scene"):
                lines.append(str(scene["scene"]))
        if not lines:
            continue
        with _lock:
            _vision[cell_id] = lines
        state = get_state()
        for point in state.heatmap:
            if point.get("point_id") == cell_id and isinstance(point.get("readings"), dict):
                point["readings"]["vision"] = lines
