"""Fit the shape thresholds on the synthetic array set and score a held-out seed."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from app.audio.detector import AcousticCalibration
from app.audio.dummy_dataset import EXPECTED, accepts, build_clip, build_dataset
from app.audio.engine import run_mics, save_calibration
from app.persistence.store import data_dir


def train_dummy(seed: int = 7) -> dict:
    clips = build_dataset(seed=seed, copies=1)
    calibration, searched = _fit(clips)
    score = _score(clips, calibration)
    held = _score(build_dataset(seed=seed + 50, copies=1), calibration)
    wavs = _write_examples(seed)
    report = {
        "training_status": "SYNTHETIC_DUMMY",
        "hardware_calibrated": False,
        "survivor_claim": False,
        "piezo_used": False,
        "train_accuracy": score["accuracy"],
        "held_out_accuracy": held["accuracy"],
        "train_misses": score["misses"],
        "held_out_misses": held["misses"],
        "clips": score["clips"],
        "grid_evaluations": searched,
        "wav_examples": wavs,
        "message": (
            "Thresholds were fit on synthetic 4-mic clips. "
            "The same rules run on the XVF3800 when it enumerates as 6 channels at 16000 Hz int16. "
            "This is not a rubble-calibrated survivor model, and there is no piezo veto."
        ),
    }
    calibration.training_status = "SYNTHETIC_DUMMY"
    calibration.hardware_calibrated = False
    report["calibration_path"] = save_calibration(calibration, report)
    report["calibration"] = calibration.to_dict()
    return report


def evaluate_dummy(seed: int = 99) -> dict:
    from app.audio.engine import load_calibration

    calibration = load_calibration()
    score = _score(build_dataset(seed=seed, copies=1), calibration)
    return {
        "training_status": calibration.training_status,
        "hardware_calibrated": False,
        "survivor_claim": False,
        "accuracy": score["accuracy"],
        "misses": score["misses"],
    }


def _score(clips: list[dict], calibration: AcousticCalibration) -> dict:
    misses = []
    for clip in clips:
        labels = {event["class"] for event in run_mics(clip["audio"], calibration)}
        if not accepts(clip["kind"], labels):
            misses.append({"kind": clip["kind"], "found": sorted(labels), "expected": sorted(EXPECTED[clip["kind"]])})
    total = len(clips)
    return {
        "accuracy": 1.0 if total == 0 else (total - len(misses)) / total,
        "misses": misses,
        "clips": total,
    }


def _fit(clips: list[dict]) -> tuple[AcousticCalibration, int]:
    base = AcousticCalibration()
    best = base
    best_accuracy = _score(clips, base)["accuracy"]
    searched = 1
    if best_accuracy >= 1.0:
        return best, searched
    for rise in (6.0, 8.0, 12.0):
        for crest in (4.5, 6.0, 8.0):
            for flatness in (0.12, 0.25, 0.4):
                for band in (0.45, 0.6, 0.75):
                    candidate = AcousticCalibration(
                        rise_ratio=rise,
                        crest_min=crest,
                        flatness_min=flatness,
                        band_fraction_min=band,
                    )
                    searched += 1
                    accuracy = _score(clips, candidate)["accuracy"]
                    if accuracy > best_accuracy:
                        best = candidate
                        best_accuracy = accuracy
                        if accuracy >= 1.0:
                            return best, searched
    return best, searched


def _write_examples(seed: int) -> list[str]:
    folder = Path(data_dir()) / "dummy_acoustic"
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for kind in ("knock", "scratch", "periodic", "whine"):
        rng = np.random.default_rng(seed + _offset(kind))
        mics = build_clip(kind, rng)
        six = np.zeros((mics.shape[0], 6), dtype=np.float64)
        six[:, :4] = mics
        pcm = np.clip(six, -1.0, 1.0)
        pcm = (pcm * 32767.0).astype("<i2")
        path = folder / f"{kind}.wav"
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(6)
            handle.setsampwidth(2)
            handle.setframerate(16000)
            handle.writeframes(pcm.tobytes())
        written.append(str(path))
    return written


def _offset(kind: str) -> int:
    return list(EXPECTED).index(kind) * 17
