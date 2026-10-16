"""Next-probe scoring: probability, unexplored area, and travel cost."""

from __future__ import annotations

import math

from reasoning.probability_map import ProbabilityMap


class SearchStrategy:
    def select(
        self,
        robot_x: float,
        robot_y: float,
        belief: ProbabilityMap,
        strategy: str,
        probed: list[tuple[float, float]],
    ) -> tuple[float, float, str]:
        if strategy == "grid":
            return self._grid(robot_x, robot_y, belief, probed)
        return self._adaptive(robot_x, robot_y, belief, probed)

    def _grid(
        self,
        robot_x: float,
        robot_y: float,
        belief: ProbabilityMap,
        probed: list[tuple[float, float]],
    ) -> tuple[float, float, str]:
        points = grid_points(belief.width, belief.height, spacing=2.0)
        for point in points:
            if _separated(point, probed, 0.8):
                return point[0], point[1], "Grid search: next point on the fixed survey pattern."
        relaxed = self._adaptive(robot_x, robot_y, belief, probed)
        return relaxed[0], relaxed[1], "Grid pattern complete. Falling back to the highest remaining score."

    def _adaptive(
        self,
        robot_x: float,
        robot_y: float,
        belief: ProbabilityMap,
        probed: list[tuple[float, float]],
    ) -> tuple[float, float, str]:
        chosen = self._best(robot_x, robot_y, belief, probed, min_sep=1.15)
        if chosen is None:
            chosen = self._best(robot_x, robot_y, belief, probed, min_sep=0.45)
        if chosen is None:
            return (
                min(belief.width - 0.5, robot_x + 1),
                min(belief.height - 0.5, robot_y + 1),
                "No open cell remained. Stepping to a nearby fallback point.",
            )
        return chosen

    def _best(
        self,
        robot_x: float,
        robot_y: float,
        belief: ProbabilityMap,
        probed: list[tuple[float, float]],
        min_sep: float,
    ) -> tuple[float, float, str] | None:
        peak = float(belief.grid.max()) + 1e-12
        span = math.hypot(belief.width, belief.height)
        best_score = -1e9
        best: tuple[float, float, str] | None = None
        for iy in range(belief.height):
            for ix in range(belief.width):
                cx = ix + 0.5
                cy = iy + 0.5
                if not _separated((cx, cy), probed, min_sep):
                    continue
                probability_score = float(belief.grid[iy, ix]) / peak
                exploration = 1.0 - min(1.0, float(belief.explored[iy, ix]))
                distance = math.hypot(cx - robot_x, cy - robot_y) / span
                score = 0.62 * probability_score + 0.22 * exploration - 0.38 * distance
                if score > best_score:
                    best_score = score
                    best = (
                        cx,
                        cy,
                        "Highest information value among unexplored cells.",
                    )
        return best


def grid_points(width: int, height: int, spacing: float = 2.0) -> list[tuple[float, float]]:
    rows: list[list[tuple[float, float]]] = []
    y = 1.0
    while y <= height - 0.5:
        row: list[tuple[float, float]] = []
        x = 1.0
        while x <= width - 0.5:
            row.append((min(x, width - 0.5), min(y, height - 0.5)))
            x += spacing
        if not row:
            break
        if len(rows) % 2 == 1:
            row.reverse()
        rows.append(row)
        y += spacing
    return [point for row in rows for point in row]


def _separated(point: tuple[float, float], probed: list[tuple[float, float]], minimum: float) -> bool:
    return all(math.hypot(point[0] - px, point[1] - py) >= minimum for px, py in probed)
