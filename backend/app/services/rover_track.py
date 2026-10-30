"""Place the map marker on the cell the rover reports."""

import json
import math
import time

from app.config.geometry import load_geometry, search_lattice
from app.services.clock import utc_now
from app.state import get_state


_cells_ok = False


def firmware_accepts_cells() -> bool:
    return _cells_ok


def reset_cell_firmware() -> None:
    global _cells_ok
    _cells_ok = False


def begin_tracking() -> None:
    state = get_state()
    state.motor_tracking = True
    state.rover_leg = None
    state.pose_trail = []
    _mark_link(state, "Rover link open. The map follows the cells the Uno reports.")


def end_tracking() -> None:
    state = get_state()
    state.motor_tracking = False
    state.rover_leg = None


def apply_rover_line(line: str) -> bool:
    text = line.strip()
    if not text.startswith("ACK "):
        return False
    try:
        payload = json.loads(text[4:])
    except json.JSONDecodeError:
        return False
    if payload.get("device") != "arduino_uno":
        return False
    state = get_state()
    state.motor_tracking = True
    places = _known_places(state)
    status = payload.get("status")
    if status == "grid_started":
        state.pose_trail = []
        state.rover_leg = None
        from app.services.cell_visit import begin_run
        from app.services.mic_window import grid_started

        begin_run()
        grid_started()
        from app.services.grid_route import reset_route

        reset_cell_firmware()
        reset_route()
        return True
    if status == "moving":
        origin = places.get(str(payload.get("from")))
        dest = places.get(str(payload.get("to")))
        if origin is None or dest is None:
            return False
        heading = math.degrees(
            math.atan2(float(dest["y_cm"]) - float(origin["y_cm"]), float(dest["x_cm"]) - float(origin["x_cm"]))
        )
        try:
            duration = max(1, int(payload.get("ms") or 1))
        except (TypeError, ValueError):
            duration = 1
        distance_cm = round(
            math.hypot(float(dest["x_cm"]) - float(origin["x_cm"]), float(dest["y_cm"]) - float(origin["y_cm"])),
            1,
        )
        state.rover_leg = {
            "from_id": origin["id"],
            "to_id": dest["id"],
            "from_x_cm": origin["x_cm"],
            "from_y_cm": origin["y_cm"],
            "to_x_cm": dest["x_cm"],
            "to_y_cm": dest["y_cm"],
            "heading_deg": round(heading, 1),
            "distance_cm": distance_cm,
            "duration_ms": duration,
            "started": time.monotonic(),
        }
        _place(state, origin, heading, f"Driving from {origin['id']} to {dest['id']}.")
        state.phase = "SCANNING"
        state.scan_stage = f"MOVE {origin['id']} {dest['id']}"
        from app.services.mic_window import hide_while_moving

        hide_while_moving()
        from app.services.grid_route import note_moving

        note_moving(str(payload.get("from")), str(payload.get("to")))
        return True
    if status == "turning":
        return _turning(state, payload)
    if status == "arrived":
        return _arrived(state, places, payload)
    if payload.get("phase") == "hold":
        cell = places.get(str(payload.get("cell")))
        if cell is None:
            return False
        leg = state.rover_leg
        heading = float(leg["heading_deg"]) if leg else float(cell.get("heading_deg") or 90.0)
        state.rover_leg = None
        _place(state, cell, heading, f"Rover reported {cell['id']} at the measured point.")
        state.pose_trail.append(dict(state.pose))
        state.phase = "SCANNING"
        state.scan_stage = f"HOLD {cell['id']}"
        from app.services.grid_route import open_sweep
        from app.services.mic_window import begin_hold

        open_sweep(str(cell["id"]), int(cell.get("heading_deg") or 0))
        begin_hold(cell)
        return True
    if status == "grid_done":
        state.rover_leg = None
        state.add_event(
            device="arduino_uno",
            sensor="motors",
            summary="Rover finished the nine squares. The marker stays on the last reported cell.",
            quality="measured",
            captured_at_utc=utc_now(),
            value=None,
            unit=None,
        )
        from app.services.cell_visit import finish_run
        from app.services.mic_window import grid_finished

        grid_finished()
        finish_run()
        return True
    if status == "scan":
        return _scan(state, payload)
    if status == "transit":
        return _transit(state, places, payload)
    return False


def _turning(state, payload: dict) -> bool:
    pose = state.pose if isinstance(state.pose, dict) else None
    if pose is None:
        return False
    try:
        heading = int(pose.get("heading_deg") or 0)
    except (TypeError, ValueError):
        heading = 0
    direction = str(payload.get("direction") or "")
    if direction == "right":
        heading = (heading + 90) % 360
    elif direction == "left":
        heading = (heading + 270) % 360
    pose["heading_deg"] = heading
    state.phase = "TURN"
    state.scan_stage = f"TURN {direction or 'square'}"
    return True


def _arrived(state, places: dict, payload: dict) -> bool:
    from app.services.grid_route import open_sweep

    global _cells_ok
    cell = places.get(str(payload.get("cell")))
    if cell is None:
        return False
    _cells_ok = True
    try:
        heading = int(payload.get("heading") or 0)
    except (TypeError, ValueError):
        heading = 0
    state.rover_leg = None
    _place(state, cell, heading, f"Stopped at {cell['id']} for the Pi sweep.")
    state.phase = "SCANNING"
    state.scan_stage = f"SWEEP {cell['id']}"
    open_sweep(str(cell["id"]), heading)
    return True


def _scan(state, payload: dict) -> bool:
    from app.services.grid_route import note_scan

    cell = str(payload.get("cell") or "")
    try:
        heading = int(payload.get("heading") or 0)
    except (TypeError, ValueError):
        heading = 0
    beams = payload.get("beams") if isinstance(payload.get("beams"), list) else []
    forward = _forward_cm(beams)
    if forward is None:
        state.ultrasonic = {
            "distance_cm": None,
            "echo_timeout": True,
            "direction": "forward",
            "source_mode": "live",
            "valid": False,
        }
    else:
        state.ultrasonic = {
            "distance_cm": forward,
            "echo_timeout": False,
            "direction": "forward",
            "source_mode": "live",
            "valid": True,
        }
    nxt = note_scan(cell, heading, beams)
    summary = f"Sweep at {cell}. Forward {forward if forward is not None else 'no echo'} cm."
    if nxt:
        summary += f" Next square is {nxt}."
    else:
        summary += " No open square remains."
    state.add_event(
        device="hc_sr04",
        sensor="ultrasonic",
        summary=summary,
        quality="sensor",
        captured_at_utc=utc_now(),
        value=forward,
        unit="cm",
        site_id=cell,
    )
    if nxt:
        from app.drivers.motor_link import send_cell

        send_cell(nxt)
    return True


def _transit(state, places: dict, payload: dict) -> bool:
    from app.services.grid_route import note_transit

    cell = places.get(str(payload.get("cell")))
    if cell is None:
        return False
    heading = float(state.pose["heading_deg"]) if state.pose else float(cell.get("heading_deg") or 0)
    _place(state, cell, heading, f"Crossing {cell['id']} to reach an open square.")
    nxt = note_transit(str(cell["id"]))
    if nxt:
        from app.drivers.motor_link import send_cell

        send_cell(nxt)
    return True


def apply_pi_sweep(beams: list) -> dict:
    """The Pi swept the square the rover is stopped on."""
    from app.drivers.motor_link import send_cell
    from app.services.grid_route import accept_beams

    result = accept_beams(beams if isinstance(beams, list) else [])
    if not result.get("ok"):
        return {"ok": False, "error": "The rover is not waiting for a sweep."}
    state = get_state()
    forward = _forward_cm(beams if isinstance(beams, list) else [])
    if forward is None:
        state.ultrasonic = {
            "distance_cm": None,
            "echo_timeout": True,
            "direction": "forward",
            "source_mode": "live",
            "valid": False,
        }
    else:
        state.ultrasonic = {
            "distance_cm": forward,
            "echo_timeout": False,
            "direction": "forward",
            "source_mode": "live",
            "valid": True,
        }
    nxt = result.get("next")
    cell = str(result.get("cell") or "")
    summary = f"Pi sweep at {cell}. Forward {forward if forward is not None else 'no echo'} cm."
    if nxt:
        summary += f" Next square is {nxt}."
        send_cell(str(nxt))
    else:
        summary += " No open square remains."
    state.add_event(
        device="hc_sr04",
        sensor="ultrasonic",
        summary=summary,
        quality="sensor",
        captured_at_utc=utc_now(),
        value=forward,
        unit="cm",
        site_id=cell,
    )
    return {"ok": True, "cell": cell, "next": nxt, "forward_cm": forward}


def _forward_cm(beams: list) -> float | None:
    closest = None
    for beam in beams:
        if not isinstance(beam, dict):
            continue
        try:
            deg = int(beam.get("deg"))
            cm = float(beam.get("cm"))
        except (TypeError, ValueError):
            continue
        if deg < 70 or deg > 110 or cm <= 0:
            continue
        if closest is None or cm < closest:
            closest = cm
    return closest


def _known_places(state) -> dict:
    """Grid cells plus the surveyed A, B, and C points from the sand-table plan."""
    places = {cell["id"]: cell for cell in (state.scan_route or search_lattice())}
    for point in load_geometry()["measurement_points"]:
        places[str(point["id"])] = {
            "id": str(point["id"]),
            "x_cm": point["x_cm"],
            "y_cm": point["y_cm"],
            "heading_deg": 90.0,
        }
    return places


def public_leg(state) -> dict | None:
    leg = state.rover_leg
    if not leg:
        return None
    elapsed = int((time.monotonic() - float(leg["started"])) * 1000)
    return {
        "from_id": leg["from_id"],
        "to_id": leg["to_id"],
        "from_x_cm": leg["from_x_cm"],
        "from_y_cm": leg["from_y_cm"],
        "to_x_cm": leg["to_x_cm"],
        "to_y_cm": leg["to_y_cm"],
        "heading_deg": leg["heading_deg"],
        "distance_cm": leg["distance_cm"],
        "duration_ms": leg["duration_ms"],
        "elapsed_ms": max(0, elapsed),
    }


def _place(state, cell: dict, heading: float, note: str) -> None:
    state.pose = {
        "x_cm": cell["x_cm"],
        "y_cm": cell["y_cm"],
        "heading_deg": round(heading, 1),
        "source": "arduino_uno",
        "valid": True,
        "error_cm": None,
        "cell_id": cell["id"],
        "captured_at_utc": utc_now(),
        "note": note,
    }
    _mark_link(state, note)


def _mark_link(state, note: str) -> None:
    for device in state.devices:
        if device.get("device_id") == "arduino_uno":
            device["state"] = "live"
            device["source_mode"] = "live"
            device["quality"] = "measured"
            device["error"] = ""
            device["last_seen_utc"] = utc_now()
            device["driver"] = note
            return
