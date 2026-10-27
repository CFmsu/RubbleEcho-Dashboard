"""Apply one bridge line to the same fields the simulation fills."""

from __future__ import annotations

from app.drivers.piezo import piezo_features
from app.drivers.serial_bridge import handle_line
from app.services.clock import utc_now
from app.services.feature_extraction import display_waveform
from app.services.signals import append_ticks, place_echo
from app.state import get_state


def apply_line(line: str) -> dict:
    handled = handle_line(line)
    kind = handled.get("kind")
    observation = handled.get("observation")
    if kind == "ultrasonic" and isinstance(observation, dict) and observation.get("distance_cm") is not None:
        _ultrasonic(observation)
    elif kind == "piezo" and isinstance(observation, dict):
        _piezo(observation)
    elif kind == "enc" and isinstance(observation, dict):
        _encoders(observation)
    return handled


def _ultrasonic(observation: dict) -> None:
    from app.services.sim_run import note_live_obstacle

    state = get_state()
    sample = dict(observation)
    sample["source_mode"] = "live"
    sample["valid"] = True
    state.ultrasonic = sample
    place_echo(state)
    _touch(state, "hc_sr04")
    if state.run_active:
        note_live_obstacle()
        place_echo(state)
    state.add_event(
        device="hc_sr04",
        sensor="ultrasonic",
        summary=f"Live ultrasonic {sample.get('distance_cm')} cm.",
        quality=sample.get("quality") or "sensor",
        captured_at_utc=utc_now(),
        value=sample.get("distance_cm"),
        unit="cm",
    )


def _piezo(observation: dict) -> None:
    raw = observation.get("samples")
    if not isinstance(raw, list):
        return
    samples = [float(value) for value in raw if isinstance(value, (int, float)) and not isinstance(value, bool)]
    if not samples:
        return
    rate = observation.get("sample_rate_hz") or 1000
    try:
        rate = float(rate)
    except (TypeError, ValueError):
        rate = 1000.0
    features = piezo_features(samples, rate, "surface_contact", observation.get("site_id"), False)
    features["source_mode"] = "live"
    state = get_state()
    state.piezo = features
    state.piezo_waveform = display_waveform(samples)
    _touch(state, "piezo")


def _encoders(observation: dict) -> None:
    left = observation.get("left_delta", observation.get("left"))
    right = observation.get("right_delta", observation.get("right"))
    if isinstance(left, list) and isinstance(right, list):
        pairs = [
            (float(a), float(b))
            for a, b in zip(left, right)
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool)
        ]
    elif isinstance(left, (int, float)) and isinstance(right, (int, float)) and not isinstance(left, bool) and not isinstance(right, bool):
        pairs = [(float(left), float(right))]
    else:
        return
    if not pairs:
        return
    state = get_state()
    for left_tick, right_tick in pairs:
        append_ticks(state, left_tick, right_tick, "live", "Encoder ticks from the motor controller.")
    if state.rover_trace is not None:
        state.rover_trace["phase"] = state.phase
    _touch(state, "arduino_uno")


def _touch(state, device_id: str) -> None:
    seen = utc_now()
    for device in state.devices:
        if device["device_id"] != device_id:
            continue
        device["state"] = "connected"
        device["source_mode"] = "live"
        device["quality"] = "sensor"
        device["last_seen_utc"] = seen
        device["age_ms"] = 0
        device["error"] = None
