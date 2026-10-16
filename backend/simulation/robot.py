"""Robot kinematic bookkeeping. This is mission motion, not rigid-body physics."""

from __future__ import annotations

import math


class SimulatedMotionAdapter:
    speed_mps = 0.45

    def heading(self, x: float, y: float, target_x: float, target_y: float) -> float:
        return math.degrees(math.atan2(target_y - y, target_x - x))

    def travel_seconds(self, distance: float) -> float:
        return max(1.4, distance / self.speed_mps)

    def interpolate(
        self,
        start_x: float,
        start_y: float,
        target_x: float,
        target_y: float,
        fraction: float,
    ) -> tuple[float, float]:
        fraction = max(0.0, min(1.0, fraction))
        return (
            start_x + (target_x - start_x) * fraction,
            start_y + (target_y - start_y) * fraction,
        )
