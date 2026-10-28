"""Accept one Raspberry Pi payload and store only the fields it actually sent."""

from __future__ import annotations

import base64
import binascii

from app.drivers.radar_mr60bha2 import blank_reading, parse_radar_line, reading_to_observation
from app.services.clock import utc_now
from app.services.sensor_feed import apply_line
from app.services.sensor_gates import enabled
from app.state import get_state

_frame: dict[str, bytes] = {}


def posted_frame(camera_id: str) -> bytes | None:
    return _frame.get(camera_id)


def ingest(payload: dict) -> dict:
    state = get_state()
    if state.mode == "simulation" and state.run_active:
        return {
            "ok": False,
            "status": 409,
            "error": "Stop the scripted demo before sending Raspberry Pi samples.",
        }
    if not isinstance(payload, dict):
        return {"ok": False, "status": 400, "error": "Raspberry Pi body must be an object."}
    if state.mode != "live":
        state.mode = "live"
    applied: list[str] = []
    skipped: list[str] = []
    lines = payload.get("lines")
    if isinstance(lines, list):
        for line in lines:
            if isinstance(line, str) and line.strip():
                if _line_allowed(line):
                    _apply_text(line.strip())
                    applied.append("line")
                else:
                    skipped.append("line")
    radar = payload.get("radar")
    if isinstance(radar, dict) and radar:
        if not enabled("radar"):
            skipped.append("radar")
        elif _apply_radar(radar):
            applied.append("radar")
    ultrasonic = payload.get("ultrasonic")
    if isinstance(ultrasonic, dict) and ultrasonic.get("distance_cm") is not None:
        if not enabled("ultrasonic"):
            skipped.append("ultrasonic")
        else:
            import json

            apply_line("ULTRASONIC " + json.dumps(ultrasonic))
            applied.append("ultrasonic")
    piezo = payload.get("piezo")
    if isinstance(piezo, dict) and isinstance(piezo.get("samples"), list):
        if not enabled("piezo"):
            skipped.append("piezo")
        else:
            import json

            apply_line("PIEZO " + json.dumps(piezo))
            applied.append("piezo")
    audio = payload.get("audio")
    if isinstance(audio, dict) and isinstance(audio.get("samples"), list) and audio.get("samples"):
        if not enabled("acoustic"):
            skipped.append("acoustic")
        elif _apply_audio(audio):
            applied.append("acoustic")
    encoders = payload.get("encoders")
    if isinstance(encoders, dict):
        import json

        apply_line("ENC " + json.dumps(encoders))
        applied.append("encoders")
    image = payload.get("camera_jpeg_base64")
    if isinstance(image, str) and image.strip():
        if not enabled("camera"):
            skipped.append("camera")
        elif _store_frame(str(payload.get("camera_id") or "camera_top"), image):
            from app.services.cell_visit import keep_frame

            keep_frame(base64.b64decode(image))
            applied.append("camera")
    if not applied and not skipped:
        return {"ok": False, "status": 400, "error": "No Raspberry Pi fields were present."}
    if applied:
        _mark_pi(state)
    state.add_event(
        device="raspberry_pi_4",
        sensor="link",
        summary=f"Recorded {', '.join(applied) or 'nothing'}. Skipped {', '.join(skipped) or 'nothing'}.",
        quality="sensor" if applied else "operator",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
    )
    if applied:
        from app.services.search_plan import _signal_kind
        from app.services.signal_review import schedule_review

        if _signal_kind(state) is not None:
            schedule_review()
    return {"ok": True, "status": 200, "applied": applied, "skipped": skipped, "mode": state.mode}


def _line_allowed(line: str) -> bool:
    text = line.strip().upper()
    if text.startswith("RADAR"):
        return enabled("radar")
    if text.startswith("ULTRASONIC"):
        return enabled("ultrasonic")
    if text.startswith("PIEZO"):
        return enabled("piezo")
    return True


def _apply_text(line: str) -> None:
    if line.startswith("RADAR "):
        observation, error = parse_radar_line(line)
        if observation is not None and not error:
            observation["source_mode"] = "live"
            observation["firmware"] = "raspberry_pi_4"
            get_state().radar = observation
            return
    apply_line(line)


def _apply_audio(audio: dict) -> bool:
    from app.services.briefing import sound_category
    from app.services.feature_extraction import classify_window

    try:
        samples = [float(sample) for sample in audio["samples"]]
        rate = float(audio.get("sample_rate") or 16000)
    except (TypeError, ValueError):
        return False
    heard = classify_window(samples, rate, utc_now(), {"site_id": None, "source_mode": "live"})
    heard["sound_category"] = sound_category(heard.get("class"))
    state = get_state()
    state.acoustic = heard
    state.add_event(
        device="raspberry_pi_4",
        sensor="acoustic",
        summary=f"Processed microphone audio: {heard['sound_category']}.",
        quality="sensor",
        captured_at_utc=utc_now(),
        value=heard.get("duration_ms"),
        unit="ms",
        acoustic_class=heard.get("class"),
    )
    return True


def _apply_radar(radar: dict) -> bool:
    reading = blank_reading()
    for key in (
        "human_presence",
        "breath_rate_bpm",
        "heart_rate_bpm",
        "num_targets",
        "distance_m",
        "distance_reported",
        "distance_unit",
        "total_phase",
        "breath_phase",
        "heart_phase",
    ):
        if key in radar:
            reading[key] = radar[key]
    try:
        observation = reading_to_observation(reading, "live", "raspberry_pi_4")
    except ValueError:
        return False
    observation["source_mode"] = "live"
    get_state().radar = observation
    return True


def _store_frame(camera_id: str, encoded: str) -> bool:
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return False
    if not raw:
        return False
    _frame[camera_id] = raw
    state = get_state()
    seen = utc_now()
    for camera in state.cameras:
        if camera.get("camera_id") != camera_id:
            continue
        camera["state"] = "connected"
        camera["source_mode"] = "live"
        camera["frame_available"] = True
        camera["last_frame_utc"] = seen
        camera["error"] = None
    return True


def _mark_pi(state) -> None:
    seen = utc_now()
    for device in state.devices:
        if device.get("device_id") != "raspberry_pi_4":
            continue
        device["state"] = "connected"
        device["source_mode"] = "live"
        device["quality"] = "sensor"
        device["last_seen_utc"] = seen
        device["age_ms"] = 0
        device["error"] = None
        device["driver"] = "POST /api/pi/ingest"
