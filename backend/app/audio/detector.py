import math

from app.services.feature_extraction import classify_window

LABELS = {
    "knock": "POSSIBLE_KNOCK",
    "scratch/scrape": "POSSIBLE_SCRATCH",
    "silence": "BACKGROUND",
    "ambient": "BACKGROUND",
    "unknown": "UNKNOWN",
}


def detect_event(samples: list[float], sample_rate: float) -> dict:
    """Local detector. It is not a trained model and it does not hear a heartbeat."""
    raw = classify_window(samples, sample_rate, context={"source_mode": "analysis"})
    rms = raw.get("rms_dbfs")
    peak = raw.get("peak_dbfs")
    centroid = raw.get("centroid_hz")
    features = {
        "rms_dbfs": rms,
        "peak_dbfs": peak,
        "centroid_hz": centroid,
        "crest": _crest(samples),
        "zero_crossing_rate": _zero_crossing_rate(samples),
    }
    return {
        "event": LABELS.get(raw["class"], "UNKNOWN"),
        "training_status": "NOT_TRAINED",
        "score": None,
        "features": features,
        "finite": _finite(features),
        "heartbeat": "UNVERIFIED",
        "limitations": raw.get("limitations", []),
        "unit_note": "dBFS is digital full scale, not sound pressure.",
    }


def _crest(samples: list[float]) -> float | None:
    if not samples:
        return None
    peak = max(abs(sample) for sample in samples)
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    if rms <= 1e-12:
        return None
    return peak / rms


def _zero_crossing_rate(samples: list[float]) -> float | None:
    if len(samples) < 2:
        return None
    crossings = 0
    for left, right in zip(samples, samples[1:]):
        if left == 0 or right == 0:
            continue
        if (left > 0) != (right > 0):
            crossings += 1
    return crossings / (len(samples) - 1)


def _finite(features: dict) -> bool:
    for value in features.values():
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if not math.isfinite(value):
            return False
    return True
