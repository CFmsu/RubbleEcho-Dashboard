import json

from app.config.settings import serial_port
from app.drivers.base import next_backoff_seconds
from app.drivers.radar_mr60bha2 import parse_radar_line
from app.drivers.ultrasonic import parse_ultrasonic


def bridge_status() -> dict:
    port = serial_port()
    if not port:
        return {
            "started": False,
            "port": None,
            "state": "disconnected",
            "reason": "NEEDS_HARDWARE_VERIFICATION",
        }
    return {
        "started": False,
        "port": port,
        "state": "configured_not_opened",
        "reason": "Serial open is not attempted by the default service process.",
    }


def handle_line(line: str) -> dict:
    """Classify one bridge line. Unprefixed status text is ignored on purpose."""
    text = line.strip()
    if text.startswith("RADAR "):
        observation, error = parse_radar_line(text)
        return {"kind": "radar", "observation": observation, "error": error}
    if text.startswith("ULTRASONIC "):
        try:
            payload = json.loads(text[len("ULTRASONIC ") :])
        except json.JSONDecodeError:
            return {"kind": "ultrasonic", "observation": None, "error": "malformed"}
        if not isinstance(payload, dict):
            return {"kind": "ultrasonic", "observation": None, "error": "malformed"}
        return {
            "kind": "ultrasonic",
            "observation": parse_ultrasonic(payload),
            "error": None,
        }
    if text.startswith("PIEZO ") or text.startswith("ENC "):
        kind, _, body = text.partition(" ")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return {"kind": kind.lower(), "observation": None, "error": "malformed"}
        if not isinstance(payload, dict):
            return {"kind": kind.lower(), "observation": None, "error": "malformed"}
        return {"kind": kind.lower(), "observation": payload, "error": None}
    if text.startswith("ACK "):
        return {"kind": "ack", "observation": None, "error": None}
    return {"kind": "ignored", "observation": None, "error": None}


def backoff_sequence(attempts: int) -> list[float]:
    return [next_backoff_seconds(index) for index in range(attempts)]
