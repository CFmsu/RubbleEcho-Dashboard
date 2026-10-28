"""Place the map marker on the cell the rover reports."""

import json
import math
import time

from app.config.geometry import load_geometry, search_lattice
from app.services.clock import utc_now
from app.state import get_state


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
        state.rover_leg = {
            "from_id": origin["id"],
            "to_id": dest["id"],
            "from_x_cm": origin["x_cm"],
            "from_y_cm": origin["y_cm"],
            "to_x_cm": dest["x_cm"],
            "to_y_cm": dest["y_cm"],
            "heading_deg": round(heading, 1),
            "duration_ms": duration,
            "started": time.monotonic(),
        }
        _place(state, origin, heading, f"Driving from {origin['id']} to {dest['id']}.")
        state.phase = "SCANNING"
        state.scan_stage = f"MOVE {origin['id']} {dest['id']}"
        return True
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
        return True
    if status == "grid_done":
        state.rover_leg = None
        state.add_event(
            device="arduino_uno",
            sensor="motors",
            summary="Rover finished the measured grid. The marker stays on the last reported cell.",
            quality="measured",
            captured_at_utc=utc_now(),
            value=None,
            unit=None,
        )
        return True
    return False


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
