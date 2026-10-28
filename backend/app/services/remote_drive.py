"""Hand remote. Directions go to the Bluetooth sketch. The model never drives."""

from __future__ import annotations

from app.drivers.motor_link import transmit
from app.services.clock import utc_now
from app.services.sensor_gates import public_gates, set_gate
from app.state import get_state

_DIRECTIONS = {"F": "forward", "B": "back", "L": "left", "R": "right", "S": "stop"}
_last = {"command": None, "sent": False, "port": None, "reason": None}


def public_remote() -> dict:
    return {
        "directions": _DIRECTIONS,
        "last": dict(_last),
        "sensors": public_gates(),
        "drives_itself": False,
    }


def drive_command(command: str) -> dict:
    letter = (command or "").strip().upper()[:1]
    if letter not in _DIRECTIONS:
        return {"ok": False, "status": 400, "error": "Use F, B, L, R, or S."}
    link = transmit(letter)
    changed = _last["command"] != letter
    _last.update(
        {
            "command": letter,
            "sent": bool(link.get("sent")),
            "port": link.get("port"),
            "reason": link.get("reason"),
        }
    )
    state = get_state()
    if changed:
        state.add_event(
            device="arduino_uno",
            sensor="motors",
            summary=f"Remote {_DIRECTIONS[letter]}. The model did not command this.",
            quality="transmitted" if link.get("sent") else "unavailable",
            captured_at_utc=utc_now(),
            value=None,
            unit=None,
        )
    return {
        "ok": True,
        "status": 200,
        "command": letter,
        "rover": link,
        "drives_itself": False,
    }


def set_sensor(name: str, on: bool) -> dict:
    result = set_gate(name, on)
    if not result["ok"]:
        return result
    state = get_state()
    state.add_event(
        device="raspberry_pi_4",
        sensor=name,
        summary=f"{name} {'measuring' if on else 'stopped'}.",
        quality="operator",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
    )
    return result
