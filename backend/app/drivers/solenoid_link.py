"""Send the Arduino solenoid sketch a one-line command. This does not open the radar port."""

import os

_RADAR_VIDS = ("303A", "2886")
_BOARD_NEEDLES = ("arduino", "ch340", "wch.cn", "1a86", "2341", "2a03", "ftdi", "0403")


def solenoid_port(ports: list | None = None) -> str | None:
    chosen = os.environ.get("RUBBLEECHO_SOLENOID_PORT", "").strip()
    if chosen:
        return chosen
    found = ports if ports is not None else _listed_ports()
    matches = []
    for port in found:
        blob = f"{getattr(port, 'device', '')} {getattr(port, 'description', '')} {getattr(port, 'hwid', '')}".lower()
        if any(vid.lower() in blob for vid in _RADAR_VIDS):
            continue
        if "espressif" in blob or "jtag" in blob:
            continue
        if any(needle in blob for needle in _BOARD_NEEDLES):
            matches.append(port)
    if len(matches) == 1:
        return str(matches[0].device)
    return None


def transmit(command: str, write=None) -> dict:
    """Write KNOCK, START, or STOP. `write(port, command)` is injectable in tests."""
    port = solenoid_port()
    if command not in {"KNOCK", "START", "STOP"}:
        return {"sent": False, "port": port, "command": command, "reason": "rejected"}
    if not port:
        return {"sent": False, "port": None, "command": command, "reason": "arduino_not_found"}
    sender = write or _serial_write
    try:
        sender(port, command)
    except Exception as exc:
        return {
            "sent": False,
            "port": port,
            "command": command,
            "reason": "serial_error",
            "error": type(exc).__name__,
        }
    return {"sent": True, "port": port, "command": command, "reason": "sent"}


def _listed_ports() -> list:
    try:
        from serial.tools import list_ports
    except Exception:
        return []
    try:
        return list(list_ports.comports())
    except Exception:
        return []


def _serial_write(port: str, command: str) -> None:
    import serial

    with serial.Serial(port, 115200, timeout=0.2, write_timeout=0.5) as link:
        link.write(f"{command}\n".encode("ascii"))
