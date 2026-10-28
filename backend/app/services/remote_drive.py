"""Hand remote. Directions go to the Bluetooth sketch. The model never drives."""

from __future__ import annotations

from app.drivers.motor_link import transmit
from app.services.clock import utc_now
from app.services.sensor_gates import public_gates, set_gate
from app.state import get_state

_DIRECTIONS = {"F": "forward", "B": "back", "L": "left", "R": "right", "S": "stop"}
_last = {"command": None, "sent": False, "port": None, "reason": None}
_mode = "stopped"


def public_remote() -> dict:
    from app.services.auto_listen import public_auto

    auto = public_auto()
    return {
        "directions": _DIRECTIONS,
        "last": dict(_last),
        "sensors": public_gates(),
        "mode": _mode,
        "step": auto["step"],
        "stopped": _mode != "auto",
        "drives_itself": False,
    }


def hold_stopped() -> None:
    """Drop back to the initial hold. The phone pad can still drive after this."""
    global _mode
    from app.services.auto_listen import cancel

    cancel()
    _mode = "stopped"


def mark_auto() -> None:
    global _mode
    _mode = "auto"


def reset_remote() -> None:
    global _mode
    hold_stopped()
    _mode = "stopped"
    _last.update({"command": None, "sent": False, "port": None, "reason": None})


def set_mode(mode: str) -> dict:
    global _mode
    if mode not in {"manual", "auto"}:
        return {"ok": False, "status": 400, "error": "Use auto or manual."}
    if mode == "manual":
        from app.services.auto_listen import cancel

        cancel()
        _mode = "manual"
        link = transmit("S")
        _last.update(
            {
                "command": "S",
                "sent": bool(link.get("sent")),
                "port": link.get("port"),
                "reason": link.get("reason"),
            }
        )
    else:
        _mode = "auto"
    state = get_state()
    state.add_event(
        device="arduino_uno",
        sensor="motors",
        summary="Manual drive from the phone." if mode == "manual" else "Auto is selected. The rover stays stopped until it is armed.",
        quality="operator",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
    )
    return {"ok": True, "status": 200, **public_remote()}


def drive_command(command: str) -> dict:
    global _mode
    letter = (command or "").strip().upper()[:1]
    if letter not in _DIRECTIONS:
        return {"ok": False, "status": 400, "error": "Use F, B, L, R, or S."}
    if letter != "S" and _mode == "auto":
        return {
            "ok": True,
            "status": 200,
            "command": letter,
            "rover": {"sent": False, "port": None, "command": letter, "reason": "auto_sampling"},
            "drives_itself": False,
            "mode": _mode,
        }
    if letter != "S" and _mode == "stopped":
        _mode = "manual"
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
        "mode": _mode,
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
