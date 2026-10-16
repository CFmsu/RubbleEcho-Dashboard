"""Simulated semantic camera. A future inference adapter can replace this module."""

from __future__ import annotations

from models.sensors import CameraObservation
from simulation.environment import Environment


class CameraAdapter:
    def observe(self, env: Environment, x: float, y: float) -> CameraObservation:
        raise NotImplementedError


class SimulatedCameraAdapter(CameraAdapter):
    def observe(self, env: Environment, x: float, y: float) -> CameraObservation:
        density = env.debris_density(x, y)
        distance = env.distance_to_survivor(x, y)
        visible_void = distance < 1.35 and density < 0.82
        safe = density < 0.93
        if visible_void:
            note = "Synthetic view: possible void along the contact face."
        elif density > 0.8:
            note = "Synthetic view: dense debris. Probe with caution."
        else:
            note = "Synthetic view: contact surface appears reachable."
        return CameraObservation(
            surface_type=env.surface,
            debris_density=round(density, 3),
            visible_void=visible_void,
            safe_to_probe=safe,
            note=note,
        )
