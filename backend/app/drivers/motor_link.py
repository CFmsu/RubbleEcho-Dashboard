"""Send one pilot character to the rover Uno and keep the port open so the map can track it."""

import os
import threading
import time

_RADAR_VIDS = ("303A", "2886")
_BOARD_NEEDLES = ("arduino", "ch340", "wch.cn", "1a86", "2341", "2a03")
_lock = threading.Lock()
_link = None
_reader: threading.Thread | None = None
_ready = False


def motor_port(ports: list | None = None) -> str | None:
    chosen = os.environ.get("RUBBLEECHO_MOTOR_PORT", "").strip()
    if chosen:
        return chosen
    solenoid = os.environ.get("RUBBLEECHO_SOLENOID_PORT", "").strip()
    found = ports if ports is not None else _listed_ports()
    matches = []
    for port in found:
        device = str(getattr(port, "device", ""))
        if solenoid and device.lower() == solenoid.lower():
            continue
        blob = f"{device} {getattr(port, 'description', '')} {getattr(port, 'hwid', '')}".lower()
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
    """Write A to start the measured grid, or S to stop. Baud is 9600, matching the sketch."""
    if command not in {"A", "F", "B", "L", "R", "S"}:
        return {"sent": False, "port": None, "command": command, "reason": "rejected"}
    if write is None and os.environ.get("PYTEST_CURRENT_TEST"):
        return {"sent": False, "port": None, "command": command, "reason": "not_sent"}
    if write is not None:
        port = motor_port()
        if not port:
            return {"sent": False, "port": None, "command": command, "reason": "rover_not_found"}
        write(port, command)
        return {"sent": True, "port": port, "command": command, "reason": "sent"}
    port = motor_port()
    if not port:
        return _queue_pi(command)
    if command == "S" and not _held_open():
        from app.services.rover_track import end_tracking

        end_tracking()
        return {"sent": False, "port": None, "command": command, "reason": "rover_not_open"}
    if command == "A":
        from app.services.rover_track import begin_tracking

        begin_tracking()
    try:
        _send(port, command)
    except Exception:
        if command == "A":
            from app.services.rover_track import end_tracking

            end_tracking()
        return _queue_pi(command)
    if command == "S":
        from app.services.rover_track import end_tracking

        end_tracking()
    return {"sent": True, "port": port, "command": command, "reason": "sent"}


def send_speed(level: int) -> dict:
    """Set the manual PWM. The grid still uses full power on its own moves."""
    command = str(level)
    if command not in "0123456789":
        return {"sent": False, "port": None, "command": command, "reason": "rejected"}
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return {"sent": False, "port": None, "command": command, "reason": "not_sent"}
    port = motor_port()
    if not port or not _held_open():
        from app.services.pi_link import enqueue

        enqueue(command)
        return {"sent": True, "port": "pi", "command": command, "reason": "queued"}
    try:
        _send(port, command)
    except Exception:
        from app.services.pi_link import enqueue

        enqueue(command)
        return {"sent": True, "port": "pi", "command": command, "reason": "queued"}
    return {"sent": True, "port": port, "command": command, "reason": "sent"}


def send_cell(cell_id: str) -> dict:
    """Queue one adjacent square. The Uno drives it after the current stop."""
    command = f"C{cell_id}\n"
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return {"sent": False, "port": None, "command": command.strip(), "reason": "not_sent"}
    from app.services.rover_track import firmware_accepts_cells

    if not firmware_accepts_cells():
        return {"sent": False, "port": "pi", "command": command.strip(), "reason": "board_drives_the_squares"}
    port = motor_port()
    if not port or not _held_open():
        from app.services.pi_link import enqueue

        enqueue(command)
        return {"sent": True, "port": "pi", "command": command.strip(), "reason": "queued"}
    try:
        _send(port, command)
    except Exception as exc:
        return {
            "sent": False,
            "port": port,
            "command": command.strip(),
            "reason": "serial_error",
            "error": type(exc).__name__,
        }
    return {"sent": True, "port": port, "command": command.strip(), "reason": "sent"}


def _queue_pi(command: str) -> dict:
    from app.services.pi_link import enqueue

    if command == "A":
        from app.services.rover_track import begin_tracking

        begin_tracking()
    enqueue(command)
    if command == "S":
        from app.services.rover_track import end_tracking

        end_tracking()
    return {"sent": True, "port": "pi", "command": command, "reason": "queued"}


def _held_open() -> bool:
    link = _link
    return bool(link is not None and getattr(link, "is_open", False))


def _send(port: str, command: str) -> None:
    global _ready
    link, fresh = _ensure(port)
    with _lock:
        if fresh or not _ready:
            _wait_ready(link)
            _ready = True
        link.write(command.encode("ascii"))
        link.flush()
    _start_reader()


def _ensure(port: str):
    global _link, _ready
    current = _link
    if current is not None and getattr(current, "is_open", False) and getattr(current, "port", None) == port:
        return current, False
    import serial

    with _lock:
        if _link is not None:
            try:
                _link.close()
            except Exception:
                pass
        link = serial.Serial()
        link.port = port
        link.baudrate = 9600
        link.timeout = 0.2
        link.write_timeout = 0.5
        link.open()
        _link = link
        _ready = False
    return link, True


def _wait_ready(link) -> None:
    deadline = time.time() + 3.0
    buf = ""
    while time.time() < deadline:
        chunk = link.read(128)
        if not chunk:
            continue
        buf += chunk.decode("utf-8", errors="replace")
        if "Ready" in buf:
            return


def _start_reader() -> None:
    global _reader
    if _reader is not None and _reader.is_alive():
        return
    _reader = threading.Thread(target=_read_loop, name="rover-track", daemon=True)
    _reader.start()


def _read_loop() -> None:
    from app.services.rover_track import apply_rover_line

    buf = b""
    while True:
        link = _link
        if link is None or not getattr(link, "is_open", False):
            time.sleep(0.1)
            continue
        try:
            with _lock:
                chunk = link.read(128)
        except Exception:
            time.sleep(0.2)
            continue
        if not chunk:
            continue
        buf += chunk
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            apply_rover_line(raw.decode("utf-8", errors="replace"))


def _listed_ports() -> list:
    try:
        from serial.tools import list_ports
    except Exception:
        return []
    try:
        return list(list_ports.comports())
    except Exception:
        return []
