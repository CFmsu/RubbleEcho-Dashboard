"""Synthetic piezo contact waveforms: knock impulse, decay, and cavity reflection."""

from __future__ import annotations

import math
import random

from models.sensors import VibrationReading, Waveform


def generate_vibration(
    confidence: float,
    cavity: float,
    rng: random.Random,
    n: int = 96,
) -> VibrationReading:
    samples: list[float] = []
    peak_scale = 0.25 + 0.75 * confidence
    for i in range(n):
        t = i / (n - 1)
        noise = rng.uniform(-0.03, 0.03)
        impulse = math.exp(-t * 7.5) * math.sin(2 * math.pi * 14 * t) * peak_scale
        reflection_env = math.exp(-((t - 0.42) ** 2) / 0.008)
        reflection = reflection_env * math.sin(2 * math.pi * 22 * t) * cavity * 0.85
        samples.append(round(max(-1.0, min(1.0, impulse + reflection + noise)), 4))
    energy = sum(s * s for s in samples) / n
    peak = max(abs(s) for s in samples) if samples else 0.0
    frequency = 16 + (1.0 - cavity) * 28 + confidence * 6
    return VibrationReading(
        peak_amplitude=round(peak, 4),
        signal_energy=round(energy, 4),
        cavity_response=round(cavity, 4),
        confidence=round(confidence, 4),
        dominant_frequency_hz=round(frequency, 2),
        waveform=Waveform(samples=samples),
    )
