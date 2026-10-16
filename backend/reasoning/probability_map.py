"""Spatial belief map. The update rule is an understandable approximation, not a full Bayesian filter."""

from __future__ import annotations

import math

import numpy as np


class ProbabilityMap:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid = np.full((height, width), 1.0 / (width * height), dtype=float)
        self.visits = np.zeros((height, width), dtype=int)
        self.explored = np.zeros((height, width), dtype=float)

    def update(self, x: float, y: float, strength: float) -> None:
        ys, xs = np.mgrid[0 : self.height, 0 : self.width]
        centers_x = xs + 0.5
        centers_y = ys + 0.5
        dist = np.sqrt((centers_x - x) ** 2 + (centers_y - y) ** 2)
        sigma = 1.65
        spatial = np.exp(-0.5 * (dist / sigma) ** 2)
        baseline = 0.22
        factor = 1.0 + (float(strength) - baseline) * 2.6 * spatial
        factor = np.clip(factor, 0.42, 4.2)
        self.grid *= factor
        total = float(self.grid.sum())
        if total <= 0:
            self.grid[:] = 1.0 / self.grid.size
        else:
            self.grid /= total
        ix, iy = self._index(x, y)
        self.visits[iy, ix] += 1
        self.explored[iy, ix] = 1.0
        self.explored = np.maximum(self.explored, spatial * 0.45)

    def highest_probability(self) -> tuple[float, float, float]:
        index = int(np.argmax(self.grid))
        iy, ix = divmod(index, self.width)
        return float(ix + 0.5), float(iy + 0.5), float(self.grid[iy, ix])

    def centroid(self) -> tuple[float, float]:
        threshold = float(np.quantile(self.grid, 0.85))
        mask = self.grid >= threshold
        if not np.any(mask):
            x, y, _ = self.highest_probability()
            return x, y
        ys, xs = np.mgrid[0 : self.height, 0 : self.width]
        weights = np.where(mask, self.grid, 0.0)
        total = float(weights.sum())
        cx = float(((xs + 0.5) * weights).sum() / total)
        cy = float(((ys + 0.5) * weights).sum() / total)
        return cx, cy

    def get_map(self) -> list[list[float]]:
        return [[round(float(value), 5) for value in row] for row in self.grid]

    def _index(self, x: float, y: float) -> tuple[int, int]:
        ix = int(min(max(math.floor(x), 0), self.width - 1))
        iy = int(min(max(math.floor(y), 0), self.height - 1))
        return ix, iy
