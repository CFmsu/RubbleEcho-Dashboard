"""MR60BHA2 link. Dummy samples and a live serial reader share one observation."""

from __future__ import annotations

import os
import threading
import time

from app.drivers.radar_mr60bha2 import (
    apply_esphome_line,
    blank_reading,
    dummy_sample,
    parse_binary_frames,
    parse_radar_line,
    parse_radar_object,
    reading_to_observation,
)
from app.services.clock import utc_now

_LOCK = threading.Lock()
_STOP = threading.Event()
_THREAD: threading.Thread | None = None
_MODE: str | None = None
_LAST_KEY: tuple | None = None

_NAME_NEEDLES = ("jtag", "esp32", "xiao", "seeed", "mr60", "espressif")
_VIDS = ("303A", "2886")


def device_report() -> dict:
    try:
        from serial.tools import list_ports
    except ImportError:
        return _report(None, "disconnected", "pyserial is not installed. Install backend/requirements.txt before plugging in the MR60BHA2.")
    try:
        ports = list(list_ports.comports())
    except Exception as exc:
        return _report(None, "disconnected", f"Serial port query failed: {exc}")
    override = os.environ.get("RUBBLEECHO_SERIAL_PORT", "").strip()
    if override:
        match = next((port for port in ports if port.device.lower() == override.lower()), None)
        if match is None:
            return _report(override, "disconnected", f"{override} is set but not present. Plug in the XIAO and check the COM port.")
        return _report(match.device, "ready", None, description=match.description, hwid=match.hwid)
    match = _match_port(ports)
    if match is None:
        listed = ", ".join(port.device for port in ports) or "none"
        return _report(
            None,
            "disconnected",
            f"MR60BHA2 / XIAO was not enumerated. Visible serial ports: {listed}. "
            "Set RUBBLEECHO_SERIAL_PORT if the name is not ESP32, XIAO, Seeed, or USB JTAG.",
        )
    return _report(match.device, "ready", None, description=match.description, hwid=match.hwid)


def start_dummy() -> dict:
    stop_radar()
    _start("dummy", _dummy_loop)
    return {
        "ok": True,
        "message": "Showing dummy MR60BHA2 fields. Presence, breath, heart, distance, targets, and illuminance. The module is not connected.",
    }


def start_listener() -> dict:
    report = device_report()
    if report["state"] != "ready":
        _mark(report, streaming=False)
        return {"ok": False, "message": report["error"], "report": report}
    stop_radar()
    _start("live", _serial_loop, report)
    return {
        "ok": True,
        "message": f"Reading {report['port']}. ESPHome log lines and MR60BHA2 frames use the same fields.",
        "report": report,
    }


def stop_radar() -> dict:
    global _MODE, _LAST_KEY
    _STOP.set()
    _LAST_KEY = None
    thread = _THREAD
    if thread is not None and thread.is_alive() and threading.current_thread() is not thread:
        thread.join(timeout=2.0)
    _MODE = None
    from app.state import get_state

    get_state().radar = None
    _mark(device_report(), streaming=False)
    return {"ok": True, "message": "Radar feed stopped."}


def _start(mode: str, target, report: dict | None = None) -> None:
    global _THREAD, _MODE
    with _LOCK:
        _STOP.clear()
        _MODE = mode
        args = (report,) if report is not None else ()
        _THREAD = threading.Thread(target=target, args=args, name=f"mr60bha2-{mode}", daemon=True)
        _THREAD.start()


def _dummy_loop() -> None:
    _mark({"firmware_mode": "dummy_mr60bha2", "port": None, "error": None, "state": "ready"}, streaming=True, dummy=True)
    while not _STOP.is_set():
        _publish_dummy(time.time())
        _STOP.wait(1.0)


def _serial_loop(report: dict) -> None:
    import serial

    _mark(report, streaming=True, dummy=False)
    reading = blank_reading()
    binary = bytearray()
    text = bytearray()
    try:
        port = serial.Serial(report["port"], 115200, timeout=0.2)
    except Exception as exc:
        failed = dict(report)
        failed["state"] = "disconnected"
        failed["error"] = f"Could not open {report['port']}: {exc}"
        _mark(failed, streaming=False)
        return
    try:
        while not _STOP.is_set():
            chunk = port.read(256)
            if not chunk:
                continue
            binary.extend(chunk)
            for update in parse_binary_frames(binary):
                reading.update(update)
                _publish(reading_to_observation(reading, "live", "seeed_mr60bha2"))
            text.extend(chunk)
            while b"\n" in text:
                raw, _, text = text.partition(b"\n")
                line = raw.decode("utf-8", "ignore").strip()
                if not line:
                    continue
                if line.startswith("RADAR ") or line.startswith("{"):
                    observation, error = parse_radar_line(line if line.startswith("RADAR ") else line)
                    if observation is not None:
                        observation["source_mode"] = "live"
                        observation["firmware"] = observation.get("firmware") or "seeed_mr60bha2"
                        _publish(observation)
                    continue
                if apply_esphome_line(reading, line):
                    _publish(reading_to_observation(reading, "live", "seeed_mr60bha2_esphome"))
    except Exception as exc:
        failed = dict(report)
        failed["state"] = "disconnected"
        failed["error"] = f"Radar stream failed: {exc}"
        _mark(failed, streaming=False)
    finally:
        port.close()
        if not _STOP.is_set():
            _mark(report, streaming=False)


def _publish_dummy(seconds: float) -> None:
    observation, error = parse_radar_object(dummy_sample(seconds))
    if observation is None:
        return
    observation["source_mode"] = "simulation"
    observation["case_name"] = "dummy_mr60bha2"
    observation["display_bearing_deg"] = None
    observation["notes"] = list(observation["notes"]) + [
        "dummy sample of the fields this module reports",
        "the MR60BHA2 is not connected",
    ]
    _publish(observation)


def _publish(observation: dict) -> None:
    global _LAST_KEY
    from app.state import get_state

    state = get_state()
    public = dict(observation)
    public["captured_at_utc"] = public.get("captured_at_utc") or utc_now()
    state.radar = public
    breath = public.get("breath_rate_bpm")
    heart = public.get("heart_rate_bpm")
    key = (
        public.get("source_mode"),
        public.get("human_presence"),
        None if breath is None else round(float(breath)),
        None if heart is None else round(float(heart)),
    )
    if key == _LAST_KEY:
        return
    _LAST_KEY = key
    state.add_event(
        device="mr60bha2",
        sensor="radar",
        summary=_summary(public),
        quality="dummy" if public.get("source_mode") == "simulation" else "sensor",
        captured_at_utc=public["captured_at_utc"],
        value=public.get("breath_rate_bpm"),
        unit="breaths/min",
    )


def _summary(observation: dict) -> str:
    presence = "present" if observation.get("human_presence") else "no person"
    breath = observation.get("breath_rate_bpm")
    heart = observation.get("heart_rate_bpm")
    distance = observation.get("distance_m")
    return (
        f"MR60BHA2 {presence}"
        f" · breath {breath if breath is not None else '—'} breaths/min"
        f" · heart {heart if heart is not None else '—'} bpm"
        f" · {distance if distance is not None else '—'} m"
    )


def _mark(report: dict, streaming: bool, dummy: bool = False) -> None:
    from app.state import get_state

    state = get_state()
    seen = utc_now()
    for device in state.devices:
        if device["device_id"] != "mr60bha2":
            continue
        device["firmware"] = report.get("firmware_mode") or report.get("firmware")
        device["driver"] = "dummy" if dummy else "pyserial"
        device["last_seen_utc"] = seen
        device["age_ms"] = 0
        if streaming:
            device["state"] = "simulated" if dummy else "connected"
            device["source_mode"] = "simulation" if dummy else "live"
            device["quality"] = "dummy_fields" if dummy else "mr60bha2"
            device["error"] = None
        else:
            device["state"] = "disconnected"
            device["source_mode"] = "unavailable"
            device["quality"] = "not_enumerated"
            device["error"] = report.get("error") or "No live radar frames."


def _match_port(ports: list) -> object | None:
    named = []
    for port in ports:
        blob = f"{port.device} {port.description} {port.hwid}".lower()
        if any(needle in blob for needle in _NAME_NEEDLES) or any(vid.lower() in blob for vid in _VIDS):
            named.append(port)
    if len(named) == 1:
        return named[0]
    return None


def _report(port: str | None, state: str, error: str | None, description: str | None = None, hwid: str | None = None) -> dict:
    return {
        "device_id": "mr60bha2",
        "state": state,
        "port": port,
        "description": description,
        "hwid": hwid,
        "firmware_mode": "seeed_mr60bha2" if state == "ready" else "not_enumerated",
        "error": error,
        "fields": [
            "human_presence",
            "breath_rate_bpm",
            "heart_rate_bpm",
            "distance_m",
            "num_targets",
            "illuminance_lx",
        ],
        "not_reported_by_this_module": ["bearing", "target_xy_m"],
    }
