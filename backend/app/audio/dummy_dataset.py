"""Synthetic 4-mic clips used to fit the shape rules.

These are not rubble recordings. A knock is a shared exponential burst with a
known inter-mic delay. A scratch is 1–4 kHz noise held for about one second.
Tones, rumble, and the wrong durations are the negatives.
"""

from __future__ import annotations

import numpy as np

RATE_HZ = 16000
EXPECTED = {
    "silence": set(),
    "knock": {"knock"},
    "scratch": {"scratch/scrape"},
    "whine": set(),
    "rumble": set(),
    "scratch_short": set(),
    "scratch_long": set(),
    "periodic": {"knock", "periodic_tapping"},
}


def build_dataset(seed: int = 7, copies: int = 2) -> list[dict]:
    clips = []
    for copy in range(copies):
        for kind in EXPECTED:
            rng = np.random.default_rng(seed + copy * 100 + _kind_offset(kind))
            clips.append({"kind": kind, "audio": build_clip(kind, rng), "seed": seed + copy})
    return clips


def build_clip(kind: str, rng: np.random.Generator, delays: tuple[int, int, int, int] = (0, 1, -1, 2)) -> np.ndarray:
    if kind == "silence":
        return _noise(rng, _seconds(0.8), 0.004)
    if kind == "knock":
        return _knock(rng, delays, tau_samples=120, gap_s=0.0, hits=1)
    if kind == "periodic":
        return _knock(rng, delays, tau_samples=100, gap_s=0.32, hits=3)
    if kind == "scratch":
        return _sustained(rng, 1.0, (1000, 4000), 0.08)
    if kind == "scratch_short":
        return _sustained(rng, 0.2, (1000, 4000), 0.08)
    if kind == "scratch_long":
        return _sustained(rng, 2.5, (1000, 4000), 0.08)
    if kind == "whine":
        return _tone(rng, 1.0, 1800.0, 0.08)
    if kind == "rumble":
        return _tone(rng, 1.0, 80.0, 0.08)
    raise KeyError(kind)


def accepts(kind: str, labels: set[str]) -> bool:
    if kind == "periodic":
        return "periodic_tapping" in labels and "scratch/scrape" not in labels
    return labels == EXPECTED[kind]


def _kind_offset(kind: str) -> int:
    return list(EXPECTED).index(kind) * 17


def _seconds(duration: float) -> int:
    return int(RATE_HZ * duration)


def _noise(rng: np.random.Generator, count: int, level: float) -> np.ndarray:
    return rng.normal(0.0, level, size=(count, 4))


def _knock(
    rng: np.random.Generator,
    delays: tuple[int, int, int, int],
    tau_samples: int,
    gap_s: float,
    hits: int,
) -> np.ndarray:
    pre = _seconds(0.45)
    post = _seconds(0.35)
    decay_n = min(_seconds(0.02), max(32, tau_samples))
    gap = _seconds(gap_s)
    body = hits * decay_n + max(0, hits - 1) * gap
    audio = _noise(rng, pre + body + post, 0.004)
    t = np.arange(decay_n)
    # Fixed short ring, not a random burst, so crest stays above friction noise.
    click = np.exp(-t / 12.0) * np.sin(2.0 * np.pi * 2500.0 * t / RATE_HZ)
    click[0] = 1.0
    click *= 0.8 / (np.max(np.abs(click)) + 1e-9)
    for hit in range(hits):
        base = pre + hit * (decay_n + gap)
        for channel, delay in enumerate(delays):
            start = base + delay
            audio[start : start + decay_n, channel] += click
    return audio


def _sustained(rng: np.random.Generator, duration: float, band: tuple[float, float], amp: float) -> np.ndarray:
    pre = _seconds(0.45)
    body = _seconds(duration)
    post = _seconds(0.35)
    audio = _noise(rng, pre + body + post, 0.004)
    colored = _band_noise(rng, body, band, amp)
    for channel in range(4):
        audio[pre : pre + body, channel] += _band_noise(rng, body, band, amp) if channel else colored
    return audio


def _tone(rng: np.random.Generator, duration: float, frequency: float, amp: float) -> np.ndarray:
    pre = _seconds(0.45)
    body = _seconds(duration)
    post = _seconds(0.35)
    audio = _noise(rng, pre + body + post, 0.004)
    t = np.arange(body) / RATE_HZ
    wave = amp * np.sin(2.0 * np.pi * frequency * t)
    for channel in range(4):
        audio[pre : pre + body, channel] += wave
    return audio


def _band_noise(rng: np.random.Generator, count: int, band: tuple[float, float], amp: float) -> np.ndarray:
    white = rng.normal(0.0, 1.0, size=count)
    spectrum = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(count, d=1.0 / RATE_HZ)
    spectrum[(freqs < band[0]) | (freqs > band[1])] = 0
    colored = np.fft.irfft(spectrum, n=count)
    peak = float(np.max(np.abs(colored))) + 1e-9
    return colored * (amp / peak)
