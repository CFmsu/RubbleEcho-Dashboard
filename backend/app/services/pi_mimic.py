"""Play the same sensor lines a Raspberry Pi would send, without a Pi on the desk.

The numbers are a labeled stand-in. They use the live radar text, the ultrasonic
line, the contact samples, and the wheel ticks the dashboard already understands.
"""

from __future__ import annotations

import threading

from app.drivers.radar_mr60bha2 import apply_plain_radar_line, blank_reading, reading_to_observation
from app.services.clock import utc_now
from app.services.feature_extraction import display_waveform
from app.services.signals import append_ticks
from app.state import get_state

_STOP = threading.Event()
_THREAD: threading.Thread | None = None

# Same shape as the module printout: breath, heart, and distance in meters.
_STEPS = (
    {"point": "A_NEAR", "breath": 16.0, "heart": 74.0, "distance_m": 0.42, "wall_cm": 50.5, "contact": 840},
    {"point": "A_FAR", "breath": 14.0, "heart": 68.0, "distance_m": 0.78, "wall_cm": 50.5, "contact": 460},
    {"point": "C_NEAR", "breath": 12.0, "heart": 80.0, "distance_m": 0.55, "wall_cm": 16.8, "contact": 210},
    {"point": "r1c1", "breath": 0.0, "heart": 0.0, "distance_m": 0.0, "wall_cm": 84.2, "contact": 20},
    {"point": "B_FAR", "breath": 0.0, "heart": 0.0, "distance_m": 0.0, "wall_cm": 16.8, "contact": 22},
    {"point": "B_NEAR", "breath": 0.0, "heart": 0.0, "distance_m": 0.0, "wall_cm": 84.2, "contact": 28},
)


def running() -> bool:
    return _THREAD is not None and _THREAD.is_alive()


def stop_mimic() -> None:
    global _THREAD
    _STOP.set()
    thread = _THREAD
    if thread is not None and thread.is_alive() and threading.current_thread() is not thread:
        thread.join(timeout=2.0)
    _THREAD = None


def start_mimic() -> dict:
    global _THREAD
    from app.services.radar_link import stop_radar

    stop_mimic()
    stop_radar()
    _STOP.clear()
    _THREAD = threading.Thread(target=_loop, name="pi-mimic", daemon=True)
    _THREAD.start()
    return {
        "ok": True,
        "message": "Raspberry Pi mimic is playing. Breath, heart, distance, wall range, and wheel ticks follow the live line format. No Pi is connected.",
    }


def publish_step(index: int) -> dict:
    step = _STEPS[index % len(_STEPS)]
    reading = blank_reading()
    apply_plain_radar_line(reading, f"total_phase: {(index % 8) / 10:.2f}\tbreath_phase: 0.20\theart_phase: 0.10")
    apply_plain_radar_line(reading, f"breath_rate: {step['breath']:.2f}")
    apply_plain_radar_line(reading, f"heart_rate: {step['heart']:.2f}")
    apply_plain_radar_line(reading, f"distance: {step['distance_m']:.2f}")
    observation = reading_to_observation(reading, "simulation", "pi_mimic")
    observation["case_name"] = "Pi mimic"
    observation["notes"] = list(observation.get("notes") or []) + [
        f"stand-in for a Raspberry Pi sample at {step['point']}",
        "not a frame from the module on the desk",
    ]
    state = get_state()
    state.radar = observation
    state.ultrasonic = {
        "distance_cm": step["wall_cm"],
        "echo_timeout": False,
        "direction": "forward",
        "quality": "pi_mimic",
        "source_mode": "simulation",
        "valid": True,
        "notes": [f"Pi mimic wall range at {step['point']}"],
    }
    samples = [float(step["contact"]) if index < 8 else 12.0 for index in range(32)]
    state.piezo = {
        "peak_adc_counts": step["contact"],
        "sample_rate_hz": 1000,
        "source_mode": "simulation",
        "quality": "pi_mimic",
        "site_id": step["point"],
    }
    state.piezo_waveform = display_waveform(samples)
    append_ticks(state, 1.0, 1.0, "simulation", f"Pi mimic wheel ticks at {step['point']}.")
    _mark_simulated()
    return observation


def _loop() -> None:
    index = 0
    state = get_state()
    state.add_event(
        device="raspberry_pi_4",
        sensor="radar",
        summary="Raspberry Pi mimic started. The lines match the live radar printout. No Pi is plugged in.",
        quality="synthetic",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
    )
    while not _STOP.is_set():
        publish_step(index)
        index += 1
        _STOP.wait(1.0)


def _mark_simulated() -> None:
    state = get_state()
    seen = utc_now()
    for device in state.devices:
        if device["device_id"] not in {"mr60bha2", "hc_sr04", "piezo", "raspberry_pi_4"}:
            continue
        device["state"] = "simulated"
        device["source_mode"] = "simulation"
        device["quality"] = "pi_mimic"
        device["error"] = None
        device["last_seen_utc"] = seen
        device["age_ms"] = 0
        device["driver"] = "pi_mimic"
