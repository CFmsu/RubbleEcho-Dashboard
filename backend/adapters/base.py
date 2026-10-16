"""Hardware adapter seams. Simulation classes are active. Physical classes are future stubs."""

from __future__ import annotations

from models.sensors import CameraObservation, VibrationReading


class MotionAdapter:
    def travel_seconds(self, distance: float) -> float:
        raise NotImplementedError


class CameraAdapter:
    def observe(self, x: float, y: float) -> CameraObservation:
        raise NotImplementedError


class MicrophoneAdapter:
    def listen(self, audio_state: str, confidence: float):
        raise NotImplementedError


class PiezoAdapter:
    def measure(self, confidence: float, cavity: float) -> VibrationReading:
        raise NotImplementedError


class StrikerAdapter:
    def knock(self) -> dict:
        raise NotImplementedError


class ESP32MotionAdapter(MotionAdapter):
    def travel_seconds(self, distance: float) -> float:
        raise NotImplementedError("ESP32 motion adapter is not connected in this prototype.")


class USBCameraAdapter(CameraAdapter):
    def observe(self, x: float, y: float) -> CameraObservation:
        raise NotImplementedError("USB camera adapter is not connected in this prototype.")


class SerialPiezoAdapter(PiezoAdapter):
    def measure(self, confidence: float, cavity: float) -> VibrationReading:
        raise NotImplementedError("Serial piezo adapter is not connected in this prototype.")


class GPIOStrikerAdapter(StrikerAdapter):
    def knock(self) -> dict:
        raise NotImplementedError("GPIO striker adapter is not connected in this prototype.")
