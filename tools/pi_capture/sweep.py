"""Sweep the Pi sensors while the rover is stopped, then tell the laptop.

The Uno USB cable stays in the Pi. This program reads the Uno and forwards
drive commands from the laptop.

Wire these to the Raspberry Pi, not the Uno. BCM numbers are the GPIO numbers.

- Ultrasonic servo signal: GPIO 18 (physical pin 12). 5V and ground for power.
- mmWave servo signal: GPIO 19 (physical pin 35). 5V and ground for power.
- Ultrasonic trigger: GPIO 23 (physical pin 16).
- Ultrasonic echo: through a divider into GPIO 24 (physical pin 18).
  Echo to a 1k resistor, then to GPIO 24. A 2k resistor from GPIO 24 to ground.
- Share one ground between the Pi, both servos, and the ultrasonic board.
- Servo center, 90 degrees, looks forward. 0 is the rover's left. 180 is its right.

Run this on the Pi and leave it going:

    python3 sweep.py http://172.20.10.4:5173
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import threading
import time
import urllib.request
import wave
from pathlib import Path

LAPTOP = "http://172.20.10.4:5173"
ANGLES = (0, 45, 90, 135, 180)
RADAR_PORT = ""
CLOSE_CM = 5
_can_avoid = False
_ahead = threading.Event()
_uno_ready = threading.Event()
_local_lock = threading.Lock()
_local_out: list[str] = []
_gpio_lock = threading.Lock()
_job_lock = threading.Lock()
_job_running = {"deploy": False, "collect": False}
_HORN_PINS = {"ultrasonic": 18, "mmwave": 19}
_horn_servo: dict = {}
_horn_angle = {"ultrasonic": 90.0, "mmwave": 90.0}
_horn_until = {"ultrasonic": 0.0, "mmwave": 0.0}


def ping_forward_still() -> int:
    """Read the ultrasonic without moving either servo."""
    with _gpio_lock:
        try:
            from gpiozero import DigitalInputDevice, DigitalOutputDevice
        except Exception as exc:
            print("Ultrasonic was not read:", exc, flush=True)
            return -1
        trig = DigitalOutputDevice(23)
        echo = DigitalInputDevice(24)
        try:
            return ping_cm(trig, echo)
        finally:
            trig.close()
            echo.close()


def radar_cm_now() -> int | None:
    radar = read_mmwave()
    if not radar or not isinstance(radar.get("distance_m"), (int, float)):
        return None
    return int(round(float(radar["distance_m"]) * 100))


def _close(ultra_cm: int, radar_cm: int | None) -> bool:
    ultra_close = isinstance(ultra_cm, int) and 0 < ultra_cm <= CLOSE_CM
    radar_close = isinstance(radar_cm, int) and 0 < radar_cm <= CLOSE_CM
    return ultra_close or radar_close


def _open_servo(pin: int):
    from gpiozero import AngularServo

    return AngularServo(
        pin,
        min_angle=0,
        max_angle=180,
        min_pulse_width=0.0005,
        max_pulse_width=0.0025,
        initial_angle=90,
    )


def _bounded(angle: float) -> float:
    return max(0.0, min(180.0, float(angle)))


def _read_angle(servo) -> float:
    raw = getattr(servo, "angle", None)
    try:
        value = 90.0 if raw is None else float(raw)
    except (TypeError, ValueError):
        value = 90.0
    if value != value:
        value = 90.0
    return _bounded(value)


def _write_angle(servo, angle: float) -> None:
    servo.angle = _bounded(angle)


def _creep(servos, target: float, step: float = 5.0, pause: float = 0.18) -> None:
    """Move a few degrees at a time so the horns do not slew at full speed."""
    target = _bounded(target)
    for _ in range(48):
        angles = [_read_angle(servo) for servo in servos]
        if all(abs(angle - target) < 1.0 for angle in angles):
            for servo in servos:
                _write_angle(servo, target)
            return
        for servo, angle in zip(servos, angles):
            if angle < target:
                _write_angle(servo, min(target, angle + step))
            elif angle > target:
                _write_angle(servo, max(target, angle - step))
        time.sleep(pause)


def scan_servos() -> None:
    """Servos stay still. They move only when an operator commands an angle."""
    print("Servos stay still.", flush=True)


def _ensure_horn(horn: str):
    servo = _horn_servo.get(horn)
    if servo is not None:
        return servo
    try:
        from gpiozero import AngularServo

        servo = AngularServo(
            _HORN_PINS[horn],
            min_angle=0,
            max_angle=180,
            min_pulse_width=0.0005,
            max_pulse_width=0.0025,
            initial_angle=None,
        )
    except Exception as exc:
        print(horn, "servo was not opened:", exc, flush=True)
        return None
    _horn_servo[horn] = servo
    return servo


def _release_horn(horn: str) -> None:
    _horn_until[horn] = 0.0
    servo = _horn_servo.pop(horn, None)
    if servo is None:
        return
    try:
        servo.value = None
    except Exception:
        pass
    try:
        servo.close()
    except Exception:
        pass
    print(horn, "servo released", flush=True)


def _release_idle_servos() -> None:
    now = time.monotonic()
    for horn, until in list(_horn_until.items()):
        if until and now >= until:
            _release_horn(horn)


def _apply_servo(job: dict) -> None:
    """One small step. The horn is released when the operator lets go."""
    horn = str(job.get("horn") or "")
    if horn not in _HORN_PINS:
        return
    move = str(job.get("move") or "stop")
    try:
        speed = int(job.get("speed") or 3)
    except (TypeError, ValueError):
        speed = 3
    speed = max(1, min(9, speed))
    if move == "stop":
        _release_horn(horn)
        return
    step = 1.0 + (speed * 0.5)
    angle = _horn_angle[horn]
    if move == "left":
        angle = _bounded(angle - step)
    elif move == "right":
        angle = _bounded(angle + step)
    elif move == "center":
        if abs(angle - 90.0) <= step:
            angle = 90.0
        elif angle < 90.0:
            angle = _bounded(angle + step)
        else:
            angle = _bounded(angle - step)
    else:
        return
    _horn_angle[horn] = angle
    servo = _ensure_horn(horn)
    if servo is None:
        return
    try:
        _write_angle(servo, angle)
    except Exception as exc:
        print(horn, "servo was not moved:", exc, flush=True)
        _release_horn(horn)
        return
    _horn_until[horn] = time.monotonic() + 0.45
    print(horn, "servo", round(angle, 1), "speed", speed, flush=True)


def _start_job(name: str, work) -> None:
    with _job_lock:
        if _job_running.get(name):
            print(name, "is already running.", flush=True)
            return
        _job_running[name] = True

    def run() -> None:
        try:
            work()
        except Exception as exc:
            print(name, "failed:", exc, flush=True)
        finally:
            with _job_lock:
                _job_running[name] = False

    threading.Thread(target=run, daemon=True).start()


def _poll_operator(base: str) -> None:
    try:
        queued = get_json(base + "/api/pi/operator")
    except Exception as exc:
        print("Operator link was not read:", exc, flush=True)
        return
    for job in queued.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        kind = job.get("kind")
        if kind == "servo":
            _apply_servo(job)
        elif kind == "deploy":
            cell = str(job.get("cell") or "r1c1")
            print("Remote deploy", cell, flush=True)
            _start_job("deploy", lambda cell=cell: deploy_capture(cell))
        elif kind == "collect":
            cell = str(job.get("cell") or "manual")
            print("Remote collect", cell, flush=True)
            _start_job("collect", lambda cell=cell: collect_signal(cell))
    _release_idle_servos()


def _radar_signal(radar: dict | None) -> bool:
    if not radar:
        return False
    if radar.get("human_presence") is True:
        return True
    distance = radar.get("distance_m")
    return isinstance(distance, (int, float)) and not isinstance(distance, bool) and distance > 0


def _refresh_radar_port() -> str:
    """Look again for the mmWave USB serial. It may be plugged in after startup."""
    global RADAR_PORT
    try:
        from serial.tools import list_ports
    except Exception:
        return RADAR_PORT
    for port in list_ports.comports():
        blob = f"{port.device} {port.description} {port.hwid} {getattr(port, 'manufacturer', '')}".lower()
        vid = ""
        if "vid:pid=" in blob:
            vid = blob.split("vid:pid=", 1)[1][:4]
        if vid in {"303a", "2886"} or any(name in blob for name in ("seeed", "xiao", "espressif", "mmwave", "mr60")):
            if RADAR_PORT != port.device:
                print("mmWave USB", port.device, flush=True)
            RADAR_PORT = port.device
            return RADAR_PORT
    return RADAR_PORT


def _ultra_body(cm: int) -> dict:
    if isinstance(cm, int) and cm > 0:
        return {"distance_cm": cm, "echo_timeout": False, "direction": "forward"}
    return {"echo_timeout": True, "direction": "forward"}


def slow_radar_once(deadline: float) -> dict | None:
    """Read the radar where it is. Do not move either servo."""
    del deadline
    if not _refresh_radar_port():
        print("mmWave USB is not on the Pi. Both servos stay still.", flush=True)
        return None
    radar = read_mmwave()
    print("Both servos stay still.", flush=True)
    return radar


def _post_meter(ultra_cm: int, radar: dict | None) -> None:
    payload: dict = {"ultrasonic": _ultra_body(ultra_cm)}
    if radar:
        payload["radar"] = radar
    try:
        post_json(LAPTOP.rstrip("/") + "/api/pi/ingest", payload, timeout=3)
    except Exception as exc:
        print("Live meter was not posted:", exc, flush=True)


def deploy_capture(cell: str) -> None:
    """Seven seconds on row 1: ultrasonic on, one radar sweep if needed, then the file."""
    print("Deploy listen for", cell, "12 seconds.", flush=True)
    audio_box: dict = {}

    def _mic() -> None:
        audio_box["audio"] = record_mic()

    threading.Thread(target=_mic, daemon=True).start()
    deadline = time.monotonic() + 12.0
    radar = slow_radar_once(deadline)
    ultra_cm = ping_forward_still()
    while time.monotonic() < deadline:
        ultra_cm = ping_forward_still()
        print("Deploy ultrasonic", ultra_cm, flush=True)
        _post_meter(ultra_cm if isinstance(ultra_cm, int) else -1, radar)
        time.sleep(0.5)
    audio = audio_box.get("audio")
    payload: dict = {"cell": cell, "reason": False, "ultrasonic": _ultra_body(ultra_cm if isinstance(ultra_cm, int) else -1)}
    if radar:
        payload["radar"] = radar
    if audio:
        payload["audio"] = audio
    try:
        result = post_json(LAPTOP.rstrip("/") + "/api/pi/ingest", payload, timeout=15)
        print("Deploy file:", result.get("folder"), flush=True)
    except Exception as exc:
        print("Deploy file was not saved:", exc, flush=True)
    if isinstance(ultra_cm, int) and ultra_cm > 0:
        try:
            post_json(LAPTOP.rstrip("/") + "/api/pi/sweep", {"beams": [{"deg": 90, "cm": ultra_cm}]})
        except Exception as exc:
            print("Deploy sweep was not accepted:", exc, flush=True)


def collect_signal(cell: str) -> None:
    """Read the sensors where the rover already is. Do not drive."""
    print("Collect signal for", cell, flush=True)
    audio_box: dict = {}

    def _mic() -> None:
        audio_box["audio"] = record_mic()

    threading.Thread(target=_mic, daemon=True).start()
    radar = read_mmwave()
    ultra_cm = ping_forward_still()
    deadline = time.monotonic() + 8.0
    while "audio" not in audio_box and time.monotonic() < deadline:
        time.sleep(0.2)
    audio = audio_box.get("audio")
    payload: dict = {
        "cell": cell,
        "reason": False,
        "ultrasonic": _ultra_body(ultra_cm if isinstance(ultra_cm, int) else -1),
    }
    if radar:
        payload["radar"] = radar
    if audio:
        payload["audio"] = audio
    try:
        result = post_json(LAPTOP.rstrip("/") + "/api/pi/ingest", payload, timeout=20)
        print("Collect file:", result.get("folder"), flush=True)
    except Exception as exc:
        print("Collect file was not saved:", exc, flush=True)
    _post_meter(ultra_cm if isinstance(ultra_cm, int) else -1, radar)


def look_ahead() -> None:
    """Keep rolling. Turn only when the forward reading is inside 5 cm."""
    if not _ahead.is_set():
        return
    ultra_cm = ping_forward_still()
    radar_cm = radar_cm_now()
    print("Ahead ultrasonic", ultra_cm, "mmWave", radar_cm, flush=True)
    if not _close(ultra_cm, radar_cm):
        return
    _ahead.clear()
    print("Obstacle within 5 cm. Turning.", flush=True)
    if _can_avoid:
        with _local_lock:
            _local_out.append("O")


def note_board(text: str) -> None:
    global _can_avoid
    if text.startswith("Ready"):
        _uno_ready.set()
    if "This board only drives" in text:
        _can_avoid = True
    if _can_avoid and '"status":"moving"' in text:
        _ahead.set()
    if '"status":"obstacle"' in text or '"status":"arrived"' in text or "grid_done" in text:
        _ahead.clear()


def ping_cm(trig, echo) -> int:
    trig.off()
    time.sleep(0.000002)
    trig.on()
    time.sleep(0.00001)
    trig.off()
    deadline = time.monotonic() + 0.03
    while not echo.value:
        if time.monotonic() > deadline:
            return -1
    begin = time.monotonic()
    while echo.value:
        if time.monotonic() > deadline:
            return -1
    cm = (time.monotonic() - begin) * 34300 / 2
    if cm <= 0 or cm > 400:
        return -1
    return int(cm)


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body if isinstance(body, dict) else {}


def post_json(url: str, payload: dict, timeout: float = 10) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body if isinstance(body, dict) else {}


_last_ports = ""


def open_uno():
    """Open the Arduino. Do not open the mmWave USB port that prints breath_rate."""
    import serial
    from serial.tools import list_ports

    global RADAR_PORT, _last_ports
    uno = None
    lines = []
    for port in list_ports.comports():
        blob = f"{port.device} {port.description} {port.hwid} {getattr(port, 'manufacturer', '')}".lower()
        vid = ""
        if "vid:pid=" in blob:
            vid = blob.split("vid:pid=", 1)[1][:4]
        lines.append(f"Port {port.device} vid={vid or '?'} {port.description}")
        if vid in {"303a", "2886"} or any(name in blob for name in ("seeed", "xiao", "espressif", "mmwave", "mr60")):
            RADAR_PORT = port.device
            continue
        if vid in {"2341", "2a03"} or "arduino" in blob:
            uno = port.device
    listing = "\n".join(lines)
    if listing != _last_ports:
        _last_ports = listing
        if listing:
            print(listing, flush=True)
    if uno is None:
        raise RuntimeError("Arduino Uno was not in the serial list")
    link = serial.Serial()
    link.port = uno
    link.baudrate = 9600
    link.timeout = 0.05
    link.write_timeout = 0.5
    link.dsrdtr = False
    link.rtscts = False
    link.dtr = False
    link.rts = False
    link.open()
    return link, uno


def serial_pump(link, stop: threading.Event) -> None:
    base = LAPTOP.rstrip("/")
    buf = b""
    pending: list[str] = []
    opened = time.monotonic()
    ready = False
    while not stop.is_set():
        if link is None:
            try:
                link, name = open_uno()
                print("Uno open on", name, flush=True)
                buf = b""
                opened = time.monotonic()
                ready = False
            except Exception as again:
                if "not in the serial list" not in str(again):
                    print("Uno serial not open:", again, flush=True)
                time.sleep(1)
            continue
        try:
            chunk = link.read(128) or b""
        except Exception as exc:
            print("Uno dropped:", exc, flush=True)
            try:
                link.close()
            except Exception:
                pass
            link = None
            time.sleep(1.5)
            continue
        if chunk:
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                text = raw.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                print(text)
                note_board(text)
                if text.startswith("Ready"):
                    ready = True
                    print("Uno is ready.")
                pending.append(text)
        if not ready and time.monotonic() - opened > 3:
            ready = True
            print("Uno is ready.")
        if pending:
            try:
                post_json(base + "/api/pi/link", {"lines": pending})
                pending = []
            except Exception as exc:
                print("Laptop did not take the Uno lines:", exc)
        _poll_operator(base)
        if not ready:
            time.sleep(0.05)
            continue
        try:
            queued = get_json(base + "/api/pi/link")
        except Exception as exc:
            print("Laptop not reachable:", exc)
            time.sleep(0.4)
            continue
        try:
            for command in queued.get("commands") or []:
                if not isinstance(command, str) or not command:
                    continue
                link.write(command.encode("ascii"))
                link.flush()
                print("Sent to Uno:", command.strip())
            with _local_lock:
                extra = list(_local_out)
                _local_out.clear()
            for command in extra:
                link.write((command if command.endswith("\n") else command + "\n").encode("ascii"))
                link.flush()
                print("Sent to Uno:", command.strip())
        except Exception as exc:
            print("Uno dropped:", exc, flush=True)
            try:
                link.close()
            except Exception:
                pass
            link = None
            time.sleep(1.5)
            continue
        time.sleep(0.05)


def report_cell(cell: str, beams: list[dict]) -> None:
    """Send this square's real microphone, mmWave frames, and ultrasonic reading."""
    forward = next((beam.get("cm") for beam in beams if beam.get("deg") == 90), None)
    radar = read_mmwave()
    audio = record_mic()
    payload: dict = {"reason": True, "cell": cell}
    if isinstance(forward, int) and forward > 0:
        payload["ultrasonic"] = {"distance_cm": forward}
    if radar:
        payload["radar"] = radar
        print("mmWave", radar, flush=True)
    else:
        print("mmWave sent no frame", flush=True)
    if audio:
        payload["audio"] = audio
        print("Mic recorded", audio["sample_count"], "samples", flush=True)
    else:
        print("Mic recorded nothing", flush=True)
    if "ultrasonic" not in payload and "radar" not in payload and "audio" not in payload:
        print("No sensor reading for", cell, flush=True)
        return
    try:
        result = post_json(LAPTOP.rstrip("/") + "/api/pi/ingest", payload, timeout=40)
    except Exception as exc:
        print("Laptop did not take the cell:", exc, flush=True)
        return
    reasoning = result.get("reasoning") if isinstance(result.get("reasoning"), dict) else {}
    text = reasoning.get("narrative") or reasoning.get("summary")
    print("Model:", text or "no briefing", flush=True)


def record_mic() -> dict | None:
    path = Path("/tmp/rubble_cell.wav")
    for device in _mic_devices():
        for channels in (1, 2):
            command = [
                "arecord",
                "-f",
                "S16_LE",
                "-c",
                str(channels),
                "-r",
                "16000",
                "-d",
                "7",
                "-D",
                device,
                str(path),
            ]
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=12)
            except (OSError, subprocess.TimeoutExpired) as exc:
                print("Mic command failed:", exc, flush=True)
                return None
            if result.returncode == 0 and path.is_file():
                print("Mic device", device, flush=True)
                return _wav_payload(path, channels)
            if "No such file" in (result.stderr or ""):
                break
        print("Mic missed", device, flush=True)
    return None


def _mic_devices() -> list[str]:
    chosen = os.environ.get("MIC_DEVICE", "").strip()
    devices = [chosen] if chosen else []
    try:
        listed = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=3)
        for line in listed.stdout.splitlines():
            if line.startswith("card "):
                number = line.split()[1].rstrip(":")
                devices.append(f"plughw:{number}")
    except (OSError, subprocess.TimeoutExpired):
        pass
    devices.extend(["default", "plughw:1", "plughw:2", "plughw:0"])
    unique: list[str] = []
    for device in devices:
        if device and device not in unique:
            unique.append(device)
    return unique


def _wav_payload(path: Path, channels: int) -> dict | None:
    with wave.open(str(path), "rb") as handle:
        if handle.getsampwidth() != 2:
            return None
        frames = handle.readframes(handle.getnframes())
        channels = handle.getnchannels() or channels
    if len(frames) < 2:
        return None
    count = len(frames) // 2
    raw = struct.unpack("<" + "h" * count, frames[: count * 2])
    if channels > 1:
        raw = raw[::channels]
    picked = [round(raw[index] / 32768.0, 4) for index in range(0, len(raw), 10)]
    if not picked:
        return None
    return {"sample_rate": 1600, "sample_count": len(picked), "samples": picked}


def read_mmwave() -> dict | None:
    """Read the mmWave port. Keep only numbers the sensor actually prints."""
    try:
        import serial
    except ImportError:
        print("python3-serial is not installed, so mmWave was not read", flush=True)
        return None
    name = os.environ.get("MMWAVE_PORT", "").strip() or RADAR_PORT
    if not name or not Path(name).exists():
        return None
    try:
        link = serial.Serial()
        link.port = name
        link.baudrate = 9600
        link.timeout = 0.05
        link.dsrdtr = False
        link.rtscts = False
        link.dtr = False
        link.rts = False
        link.open()
    except Exception as exc:
        print("mmWave port did not open:", exc, flush=True)
        return None
    buffer = bytearray()
    try:
        deadline = time.monotonic() + 0.6
        while time.monotonic() < deadline:
            buffer.extend(link.read(128))
    except Exception as exc:
        print("mmWave read failed:", exc, flush=True)
        buffer = bytearray()
    finally:
        try:
            link.close()
        except Exception:
            pass
    text = buffer.decode("utf-8", errors="replace")
    parsed = _text_radar(text) or _mmwave_frames(buffer)
    if parsed:
        print("mmWave port", name, flush=True)
    return parsed


def _text_radar(text: str) -> dict | None:
    import re

    found: dict = {}
    for key, raw in re.findall(r"([A-Za-z_]+):\s*(-?\d+(?:\.\d+)?)", text):
        number = float(raw)
        if key == "breath_rate":
            found["breath_rate_bpm"] = number
        elif key == "heart_rate":
            found["heart_rate_bpm"] = number
        elif key in {"total_phase", "breath_phase", "heart_phase"}:
            found[key] = number
    return found or None


def _mmwave_frames(buffer: bytearray) -> dict | None:
    found: dict = {}
    while buffer:
        if buffer[0] != 0x01:
            del buffer[0]
            continue
        if len(buffer) < 8:
            break
        length = (buffer[3] << 8) | buffer[4]
        total = 9 + length
        if length > 64 or total > 80:
            del buffer[0]
            continue
        if len(buffer) < total:
            break
        frame = bytes(buffer[:total])
        del buffer[:total]
        if _xor(frame[:7]) != frame[7] or _xor(frame[8 : 8 + length]) != frame[8 + length]:
            continue
        kind = (frame[5] << 8) | frame[6]
        data = frame[8 : 8 + length]
        if kind == 0x0F09 and len(data) >= 2:
            found["human_presence"] = int.from_bytes(data[:2], "little") != 0
        elif kind == 0x0A16 and len(data) >= 8 and data[0] != 0:
            meters = struct.unpack("<f", data[4:8])[0]
            if 0 < meters < 20:
                found["distance_m"] = round(meters, 3)
        elif kind == 0x0A14 and len(data) >= 4 and data[:4] != b"\x00\x00\x00\x00":
            found["breath_rate_bpm"] = round(struct.unpack("<f", data[:4])[0], 1)
        elif kind == 0x0A15 and len(data) >= 4 and data[:4] != b"\x00\x00\x00\x00":
            found["heart_rate_bpm"] = round(struct.unpack("<f", data[:4])[0], 1)
    return found or None


def _xor(data: bytes) -> int:
    value = 0
    for byte in data:
        value ^= byte
    return (~value) & 0xFF


def sweep_loop() -> None:
    last = None
    deployed = False
    print("Waiting for the rover to stop. Sensors stay on this Pi.")
    while True:
        try:
            status = get_json(LAPTOP.rstrip("/") + "/api/pi/sweep")
        except Exception as exc:
            print("Laptop not reachable:", exc)
            time.sleep(1)
            continue
        if not _uno_ready.is_set():
            time.sleep(0.2)
            continue
        cell = status.get("cell")
        if status.get("ready") and cell and cell != last:
            last = cell
            if not deployed and cell == "r1c1":
                deployed = True
                try:
                    deploy_capture(str(cell))
                except Exception as exc:
                    print("Deploy listen failed:", exc, flush=True)
            elif not deployed:
                print("Old stop", cell, "is not row 1 square 1. Waiting for a new start.", flush=True)
            else:
                ultra_cm = ping_forward_still()
                radar = read_mmwave()
                print("Passing", cell, "ultrasonic", ultra_cm, flush=True)
                payload: dict = {"cell": cell, "reason": False}
                if isinstance(ultra_cm, int) and ultra_cm > 0:
                    payload["ultrasonic"] = {"distance_cm": ultra_cm}
                if radar:
                    payload["radar"] = radar
                if len(payload) > 2:
                    try:
                        post_json(LAPTOP.rstrip("/") + "/api/pi/ingest", payload, timeout=5)
                    except Exception as exc:
                        print("Passing sample was not saved:", exc, flush=True)
        else:
            look_ahead()
        time.sleep(0.4)


def main() -> None:
    global LAPTOP
    if len(sys.argv) > 1:
        LAPTOP = sys.argv[1]
    if LAPTOP.startswith("https://"):
        LAPTOP = "http://" + LAPTOP[len("https://") :]
    print("RubbleEcho Pi link. Laptop:", LAPTOP, flush=True)
    link = None
    while link is None:
        try:
            link, name = open_uno()
            print("Uno open on", name, flush=True)
        except Exception as exc:
            if "not in the serial list" not in str(exc):
                print("Uno serial not open:", exc, flush=True)
            time.sleep(1)
    stop = threading.Event()
    threading.Thread(target=serial_pump, args=(link, stop), daemon=True).start()
    try:
        sweep_loop()
    finally:
        stop.set()
        link.close()


if __name__ == "__main__":
    main()
