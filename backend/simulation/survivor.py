"""Shared synthetic observation model used by the live mission and the strategy comparison."""

from __future__ import annotations

import math
import random

from models.mission import SimulationConfig
from models.sensors import RawObservation
from simulation.environment import Environment


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return float(max(low, min(high, value)))


def probe_rng(seed: int, x: float, y: float) -> random.Random:
    key = seed * 100_003 + int(round(x * 10)) * 1_009 + int(round(y * 10))
    return random.Random(key)


def proximity(distance: float) -> float:
    return math.exp(-distance / 2.8)


def observe(env: Environment, x: float, y: float, config: SimulationConfig) -> RawObservation:
    distance = env.distance_to_survivor(x, y)
    prox = proximity(distance)
    rng = probe_rng(config.seed, x, y)
    noise = (rng.random() - 0.5) * config.noise_level * 0.35
    reliability = config.sensor_reliability

    vibration = clamp(0.05 + 0.92 * prox * reliability + noise)
    cavity = clamp(0.04 + 0.9 * prox * (0.65 + 0.35 * reliability) + noise * 0.6)
    visual = clamp(0.1 + 0.34 * prox * reliability)

    tap_probability = clamp((prox - 0.34) / 0.42) * config.response_probability * reliability
    roll = rng.random()
    # Very close contact is reproducible: the source is inside the sensor footprint.
    if prox >= 0.74:
        audio_state = "CONFIRMED_RESPONSE"
        audio = clamp(0.84 + 0.14 * prox)
    elif prox > 0.55 and roll < max(tap_probability, 0.35):
        audio_state = "POSSIBLE_TAP"
        audio = clamp(0.6 + 0.28 * prox)
    elif prox > 0.38:
        audio_state = "WEAK_RESPONSE"
        audio = clamp(0.22 + 0.36 * prox + noise * 0.4)
    elif roll < 0.28:
        audio_state = "AMBIENT_NOISE"
        audio = clamp(0.08 + 0.1 * prox)
    else:
        audio_state = "NO_RESPONSE"
        audio = clamp(0.05 + 0.08 * prox)

    return RawObservation(
        audio=audio,
        vibration=vibration,
        cavity=cavity,
        visual=visual,
        audio_state=audio_state,
        distance=distance,
    )
