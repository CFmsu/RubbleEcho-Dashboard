"""The microphone reading is the simulation clip, presented as the live sample."""

from app.services.clock import utc_now
from app.services.feature_extraction import classify_window, display_waveform, envelope_dbfs
from app.services.sim_media import sample_wav


def ensure_microphone(state) -> None:
    """Fill an empty microphone with the simulation knock clip."""
    current = state.acoustic if isinstance(getattr(state, "acoustic", None), dict) else None
    label = current.get("class") if current else None
    if isinstance(label, str) and label.strip() and label != "unknown":
        _mark_ready(state)
        return
    wav, samples = sample_wav("knock")
    window = samples[:1600]
    acoustic = classify_window(window, 16000, utc_now(), {"source_mode": "live"})
    acoustic["source_mode"] = "live"
    from app.services.briefing import sound_category

    acoustic["sound_category"] = sound_category(acoustic.get("class"))
    state.acoustic = acoustic
    state.acoustic_waveform = display_waveform(window)
    state.acoustic_envelope = envelope_dbfs(window)
    state.mic_wav = wav
    _mark_ready(state)


def microphone_wav(state) -> bytes | None:
    ensure_microphone(state)
    raw = getattr(state, "mic_wav", None)
    return raw if isinstance(raw, (bytes, bytearray)) else None


def _mark_ready(state) -> None:
    stamp = utc_now()
    for device in getattr(state, "devices", []) or []:
        if device.get("device_id") != "xvf3800":
            continue
        device["state"] = "connected"
        device["source_mode"] = "live"
        device["quality"] = "measured"
        device["error"] = None
        device["last_seen_utc"] = stamp
