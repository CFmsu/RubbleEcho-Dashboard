"""Simulated adapters used by the mission controller."""

from __future__ import annotations

import random

from adapters.base import MicrophoneAdapter, MotionAdapter, PiezoAdapter, StrikerAdapter
from models.sensors import AudioReading, VibrationReading
from simulation.acoustic import generate_audio
from simulation.piezo import generate_vibration
from simulation.robot import SimulatedMotionAdapter
from simulation.striker import SimulatedStrikerAdapter as _SimulatedStriker


class SimulatedMotionAdapter(MotionAdapter):
    def __init__(self) -> None:
        self._motion = SimulatedMotionAdapter()

    def travel_seconds(self, distance: float) -> float:
        return self._motion.travel_seconds(distance)

    @property
    def impl(self) -> SimulatedMotionAdapter:
        return self._motion


class SimulatedMicrophoneAdapter(MicrophoneAdapter):
    def listen(self, audio_state: str, confidence: float, rng: random.Random | None = None) -> AudioReading:
        return generate_audio(audio_state, confidence, rng or random.Random(0))


class SimulatedPiezoAdapter(PiezoAdapter):
    def measure(self, confidence: float, cavity: float, rng: random.Random | None = None) -> VibrationReading:
        return generate_vibration(confidence, cavity, rng or random.Random(1))


class SimulatedStrikerAdapter(StrikerAdapter):
    def __init__(self) -> None:
        self._striker = _SimulatedStriker()

    def knock(self, vibration: VibrationReading | None = None) -> dict:
        if vibration is None:
            return {"actuator": "simulated_solenoid", "status": "ready"}
        return self._striker.knock(vibration)
