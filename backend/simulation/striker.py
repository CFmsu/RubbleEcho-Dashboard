"""Mechanical striker / solenoid abstraction."""

from __future__ import annotations

from models.sensors import VibrationReading


class StrikerAdapter:
    def knock(self, vibration: VibrationReading) -> dict:
        raise NotImplementedError


class SimulatedStrikerAdapter(StrikerAdapter):
    def knock(self, vibration: VibrationReading) -> dict:
        return {
            "actuator": "simulated_solenoid",
            "impulse": "single",
            "peak_amplitude": vibration.peak_amplitude,
            "status": "fired",
        }
