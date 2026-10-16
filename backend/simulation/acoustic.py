"""Synthetic microphone waveforms. These are not recordings."""

from __future__ import annotations

import math
import random

from models.sensors import AudioReading, Waveform

AUDIO_LABELS = {
    "NO_RESPONSE": "No human response detected",
    "AMBIENT_NOISE": "Ambient noise only",
    "WEAK_RESPONSE": "Weak acoustic event",
    "POSSIBLE_TAP": "Possible human response detected",
    "CONFIRMED_RESPONSE": "Repeated tap pattern detected",
}


def generate_audio(state: str, confidence: float, rng: random.Random, n: int = 96) -> AudioReading:
    samples: list[float] = []
    taps = {
        "CONFIRMED_RESPONSE": (0.22, 0.48, 0.74),
        "POSSIBLE_TAP": (0.3, 0.62),
        "WEAK_RESPONSE": (0.55,),
    }.get(state, ())
    amp = 0.15 + 0.85 * confidence
    for i in range(n):
        t = i / (n - 1)
        value = rng.uniform(-0.04, 0.04) * (1.2 if state == "AMBIENT_NOISE" else 0.7)
        if state == "NO_RESPONSE":
            value *= 0.45
        for center in taps:
            width = 0.035
            env = math.exp(-((t - center) ** 2) / (2 * width * width))
            value += amp * env * math.sin(2 * math.pi * 9 * t)
        samples.append(round(max(-1.0, min(1.0, value)), 4))
    energy = sum(s * s for s in samples) / n
    peak = max(abs(s) for s in samples) if samples else 0.0
    return AudioReading(
        state=state,
        confidence=round(confidence, 4),
        label=AUDIO_LABELS.get(state, state),
        waveform=Waveform(samples=samples),
        peak=round(peak, 4),
        energy=round(energy, 4),
    )
