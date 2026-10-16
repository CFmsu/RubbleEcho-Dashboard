"""Stateless sensor-lab stimuli for the engineering page."""

from __future__ import annotations

import random

from models.sensors import RawObservation
from reasoning.sensor_fusion import fuse
from simulation.acoustic import generate_audio
from simulation.piezo import generate_vibration


STIMULI = {
    "knock": RawObservation(audio=0.08, vibration=0.34, cavity=0.12, visual=0.2, audio_state="NO_RESPONSE", distance=6),
    "human_tap": RawObservation(
        audio=0.9, vibration=0.48, cavity=0.36, visual=0.24, audio_state="POSSIBLE_TAP", distance=1.4
    ),
    "noise_burst": RawObservation(
        audio=0.22, vibration=0.3, cavity=0.18, visual=0.16, audio_state="AMBIENT_NOISE", distance=5
    ),
    "cavity_response": RawObservation(
        audio=0.28, vibration=0.62, cavity=0.84, visual=0.3, audio_state="WEAK_RESPONSE", distance=2.2
    ),
    "weak_response": RawObservation(
        audio=0.34, vibration=0.36, cavity=0.32, visual=0.2, audio_state="WEAK_RESPONSE", distance=3.4
    ),
    "strong_response": RawObservation(
        audio=0.94, vibration=0.88, cavity=0.8, visual=0.55, audio_state="CONFIRMED_RESPONSE", distance=0.4
    ),
}


def run_stimulus(name: str, seed: int = 7) -> dict:
    observation = STIMULI.get(name, STIMULI["knock"])
    rng = random.Random(seed + hash(name) % 10_000)
    audio = generate_audio(observation.audio_state, observation.audio, rng)
    vibration = generate_vibration(observation.vibration, observation.cavity, rng)
    fused = fuse(observation)
    return {
        "stimulus": name,
        "audio": audio.model_dump(),
        "vibration": vibration.model_dump(),
        "fusion": fused.model_dump(),
        "features": {
            "audio_state": observation.audio_state,
            "audio_label": audio.label,
            "peak_amplitude": vibration.peak_amplitude,
            "signal_energy": vibration.signal_energy,
            "cavity_response": vibration.cavity_response,
            "dominant_frequency_hz": vibration.dominant_frequency_hz,
        },
        "note": "Synthetic sensor-lab signals. Not a physical measurement.",
    }
