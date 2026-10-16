"""Explainable weighted fusion. This is an engineering simulation, not a validated detector."""

from __future__ import annotations

from models.mission import FusionResult
from models.sensors import RawObservation

WEIGHTS = {
    "audio": 0.35,
    "vibration": 0.30,
    "cavity": 0.20,
    "visual": 0.15,
}


def fuse(observation: RawObservation) -> FusionResult:
    combined = (
        WEIGHTS["audio"] * observation.audio
        + WEIGHTS["vibration"] * observation.vibration
        + WEIGHTS["cavity"] * observation.cavity
        + WEIGHTS["visual"] * observation.visual
    )
    return FusionResult(
        audio=round(observation.audio, 4),
        vibration=round(observation.vibration, 4),
        cavity=round(observation.cavity, 4),
        visual=round(observation.visual, 4),
        combined=round(float(combined), 4),
        weights=dict(WEIGHTS),
    )
