"""Operator switches. A sensor that is off is not measured."""

from __future__ import annotations

import threading

SENSORS = ("radar", "ultrasonic", "acoustic", "camera", "piezo")

_lock = threading.Lock()
_gates = {name: True for name in SENSORS}


def enabled(name: str) -> bool:
    with _lock:
        return bool(_gates.get(name, True))


def public_gates() -> dict:
    with _lock:
        return dict(_gates)


def set_gate(name: str, on: bool) -> dict:
    if name not in _gates:
        return {"ok": False, "status": 400, "error": "Unknown sensor."}
    with _lock:
        _gates[name] = bool(on)
        current = dict(_gates)
    if not on:
        _stop(name)
    return {"ok": True, "status": 200, "sensors": current}


def _stop(name: str) -> None:
    if name == "acoustic":
        from app.audio.engine import stop_listener

        stop_listener()
    elif name == "radar":
        from app.services.radar_link import stop_radar

        stop_radar()
