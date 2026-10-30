"""Hand remote. Directions go to the Bluetooth sketch. The model never drives."""

from __future__ import annotations

from app.drivers.motor_link import transmit
from app.services.clock import utc_now
from app.services.sensor_gates import public_gates, set_gate
from app.state import get_state

_DIRECTIONS = {"F": "forward", "B": "back", "L": "left", "R": "right", "S": "stop"}
_HORNS = {"ultrasonic", "mmwave"}
_SERVO_MOVES = {"left", "right", "center", "stop"}
_last = {"command": None, "sent": False, "port": None, "reason": None}
_mode = "stopped"
_speed = 9


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
        "speed": _speed,
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


def set_speed(level: int) -> dict:
    global _speed
    if isinstance(level, bool) or not isinstance(level, int) or level < 0 or level > 9:
        return {"ok": False, "status": 400, "error": "Speed is 0 through 9."}
    _speed = level
    from app.drivers.motor_link import send_speed

    link = send_speed(level)
    state = get_state()
    state.add_event(
        device="arduino_uno",
        sensor="motors",
        summary=f"Remote motor speed {level}. The model did not command this.",
        quality="operator",
        captured_at_utc=utc_now(),
        value=level,
        unit="step",
    )
    return {"ok": True, "status": 200, "rover": link, **public_remote()}


def set_servo(horn: str, move: str, speed: int) -> dict:
    if horn not in _HORNS:
        return {"ok": False, "status": 400, "error": "Use the ultrasonic or mmWave servo."}
    if move not in _SERVO_MOVES:
        return {"ok": False, "status": 400, "error": "Use left, right, center, or stop."}
    if isinstance(speed, bool) or not isinstance(speed, int):
        speed = 3
    speed = min(9, max(1, speed))
    from app.services.pi_link import enqueue_operator

    enqueue_operator("servo", {"horn": horn, "move": move, "speed": speed})
    return {"ok": True, "status": 200, "horn": horn, "move": move, "speed": speed, **public_remote()}


def request_deploy() -> dict:
    from app.services.pi_link import enqueue_operator

    enqueue_operator("deploy", {"cell": "r1c1"})
    state = get_state()
    state.add_event(
        device="raspberry_pi_4",
        sensor="link",
        summary="Deploy from the remote. Sensors record while the rover stays still.",
        quality="operator",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
    )
    return {"ok": True, "status": 200, "job": "deploy", **public_remote()}


def request_collect() -> dict:
    from app.services.pi_link import enqueue_operator

    enqueue_operator("collect", {"cell": "manual"})
    state = get_state()
    state.add_event(
        device="raspberry_pi_4",
        sensor="link",
        summary="Collect signal from the remote. Ultrasonic, radar, and microphone are saved. The rover is not driven.",
        quality="operator",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
    )
    return {"ok": True, "status": 200, "job": "collect", **public_remote()}


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
