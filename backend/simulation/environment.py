"""2D search environment. Only this module and the sensor simulators know the hidden source."""

from __future__ import annotations

import math
import random

from models.mission import SimulationConfig


class Environment:
    def __init__(self, config: SimulationConfig):
        self.width = config.width
        self.height = config.height
        self.config = config
        self._rng = random.Random(config.seed)
        self.survivor_x = float(config.survivor_x)
        self.survivor_y = float(config.survivor_y)
        self.surface = _surface_for(config.scenario)
        self.debris = self._build_debris()

    def distance_to_survivor(self, x: float, y: float) -> float:
        return math.hypot(x - self.survivor_x, y - self.survivor_y)

    def debris_density(self, x: float, y: float) -> float:
        ix = int(min(max(math.floor(x), 0), self.width - 1))
        iy = int(min(max(math.floor(y), 0), self.height - 1))
        return self.debris[iy][ix]

    def _build_debris(self) -> list[list[float]]:
        field: list[list[float]] = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                n = self._rng.random()
                density = 0.35 + 0.55 * n
                row.append(round(density, 3))
            field.append(row)
        return field


def _surface_for(scenario: str) -> str:
    if "flood" in scenario:
        return "mud"
    if scenario == "landslide":
        return "mixed"
    if "nepal_earthquake" in scenario:
        return "masonry"
    return "concrete"
