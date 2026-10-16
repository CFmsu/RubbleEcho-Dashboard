from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from models.mission import FusionResult


class Waveform(BaseModel):
    samples: list[float]
    sample_rate_hz: float = 128.0
    duration_s: float = 1.0


class AudioReading(BaseModel):
    state: str
    confidence: float
    label: str
    waveform: Waveform
    peak: float
    energy: float


class VibrationReading(BaseModel):
    peak_amplitude: float
    signal_energy: float
    cavity_response: float
    confidence: float
    dominant_frequency_hz: float
    waveform: Waveform


class CameraObservation(BaseModel):
    surface_type: str
    debris_density: float
    visible_void: bool
    safe_to_probe: bool
    note: str


class SensorBundle(BaseModel):
    audio: Optional[AudioReading] = None
    vibration: Optional[VibrationReading] = None
    camera: Optional[CameraObservation] = None
    fusion: Optional[FusionResult] = None


class RawObservation(BaseModel):
    """Internal sensor features before waveform packaging."""

    audio: float = Field(ge=0, le=1)
    vibration: float = Field(ge=0, le=1)
    cavity: float = Field(ge=0, le=1)
    visual: float = Field(ge=0, le=1)
    audio_state: str
    distance: float
