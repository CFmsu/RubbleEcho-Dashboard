"""Offline comparison of grid search and adaptive search on the same seeded world."""

from __future__ import annotations

import math

from models.mission import ComparisonResult, SimulationConfig, StrategyStats
from reasoning.next_probe import SearchStrategy
from reasoning.probability_map import ProbabilityMap
from reasoning.sensor_fusion import fuse
from simulation.environment import Environment
from simulation.survivor import observe


PROBE_OVERHEAD_S = 17.4
SPEED_MPS = 0.45


def run_comparison(config: SimulationConfig) -> ComparisonResult:
    grid = _simulate(config, "grid")
    adaptive = _simulate(config, "adaptive")
    return ComparisonResult(grid=grid, adaptive=adaptive)


def _simulate(config: SimulationConfig, strategy_name: str) -> StrategyStats:
    env = Environment(config)
    belief = ProbabilityMap(config.width, config.height)
    strategy = SearchStrategy()
    x, y = _start(config)
    distance = 0.0
    probes = 0
    found = False
    elapsed = 0.0
    visited: list[tuple[float, float]] = []
    limit = max(12, (config.width * config.height) // 2)

    while probes < limit and not found:
        target_x, target_y, _reason = strategy.select(x, y, belief, strategy_name, visited)
        step = math.hypot(target_x - x, target_y - y)
        distance += step
        elapsed += step / SPEED_MPS + PROBE_OVERHEAD_S
        x, y = target_x, target_y
        visited.append((x, y))
        reading = observe(env, x, y, config)
        fused = fuse(reading)
        belief.update(x, y, fused.combined)
        probes += 1
        if reading.audio_state == "CONFIRMED_RESPONSE" and fused.combined >= 0.7:
            cx, cy = x, y
            step = math.hypot(cx - x, cy - y)
            distance += step
            elapsed += step / SPEED_MPS + PROBE_OVERHEAD_S
            confirm = observe(env, cx, cy, config)
            confirm_fusion = fuse(confirm)
            belief.update(cx, cy, confirm_fusion.combined)
            probes += 1
            found = confirm.audio_state == "CONFIRMED_RESPONSE" or confirm_fusion.combined >= 0.72
            break

    return StrategyStats(
        measurements=probes,
        distance_travelled=round(distance, 1),
        simulated_minutes=round(elapsed / 60.0, 1),
        found=found,
    )


def _start(config: SimulationConfig) -> tuple[float, float]:
    return min(1.0, config.width - 1.0), min(1.0, config.height - 1.0)
