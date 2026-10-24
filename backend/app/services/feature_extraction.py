import math


def dbfs(amplitude: float) -> float | None:
    if amplitude <= 1e-12:
        return None
    return 20.0 * math.log10(amplitude)


def spectral_centroid_hz(samples: list[float], sample_rate: float) -> float | None:
    count = min(len(samples), 64)
    if count < 8 or sample_rate <= 0:
        return None
    window = samples[:count]
    weighted = 0.0
    total = 0.0
    half = count // 2
    for bin_index in range(1, half):
        real = 0.0
        imag = 0.0
        for index, sample in enumerate(window):
            angle = -2.0 * math.pi * bin_index * index / count
            real += sample * math.cos(angle)
            imag += sample * math.sin(angle)
        magnitude = math.hypot(real, imag)
        frequency = bin_index * sample_rate / count
        weighted += frequency * magnitude
        total += magnitude
    if total <= 1e-9:
        return None
    return weighted / total


def envelope_dbfs(samples: list[float], buckets: int = 40) -> list[float]:
    """Digital envelope for drawing. Exact zeros use a -80 dBFS display floor."""
    if not samples:
        return []
    size = max(1, math.ceil(len(samples) / buckets))
    envelope: list[float] = []
    for start in range(0, len(samples), size):
        chunk = samples[start : start + size]
        rms = math.sqrt(sum(value * value for value in chunk) / len(chunk))
        level = dbfs(rms)
        envelope.append(-80.0 if level is None else level)
    return envelope


def classify_window(
    samples: list[float],
    sample_rate: float,
    captured_at_utc: str | None = None,
    context: dict | None = None,
) -> dict:
    """Threshold classifier for normalized fixture or captured digital audio.

    Scores are uncalibrated. The classifier does not emit a speech class and does
    not claim that a sound came from under the sand.
    """
    context = context or {}
    limitations = [
        "uncalibrated_thresholds",
        "origin_unknown",
        "not_calibrated_to_sound_pressure",
    ]
    if context.get("motors_running"):
        limitations.append("motors_running_contamination_possible")
    if context.get("solenoid_commanded"):
        limitations.append(
            "cannot_separate_striker_self_noise_without_reference_piezo"
        )

    if not samples or sample_rate <= 0:
        return _event(
            "unknown",
            captured_at_utc,
            0.0,
            None,
            None,
            None,
            False,
            None,
            context,
            limitations + ["no_samples"],
        )

    peak = max(abs(sample) for sample in samples)
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    high_fraction = sum(1 for sample in samples if abs(sample) >= 0.1) / len(samples)
    duration_ms = 1000.0 * len(samples) / sample_rate
    centroid = spectral_centroid_hz(samples, sample_rate)

    label = "unknown"
    onset = False
    if rms < 0.01 and peak < 0.05:
        label = "silence"
    elif peak >= 0.45 and high_fraction < 0.2:
        label = "knock"
        onset = True
    elif peak >= 0.15 and high_fraction >= 0.5:
        label = "scratch/scrape"
        onset = True
    elif rms < 0.05:
        label = "ambient"
    else:
        limitations.append("speech_classifier_not_calibrated")

    raw_score = None
    if label in {"knock", "scratch/scrape"}:
        raw_score = round(min(1.0, peak), 3)

    return _event(
        label,
        captured_at_utc,
        duration_ms,
        dbfs(rms),
        dbfs(peak),
        centroid,
        onset,
        raw_score,
        context,
        limitations,
    )


def _event(
    label: str,
    captured_at_utc: str | None,
    duration_ms: float,
    rms_level: float | None,
    peak_level: float | None,
    centroid: float | None,
    onset: bool,
    raw_score: float | None,
    context: dict,
    limitations: list[str],
) -> dict:
    return {
        "class": label,
        "start_utc": captured_at_utc,
        "duration_ms": duration_ms,
        "rms_dbfs": rms_level,
        "peak_dbfs": peak_level,
        "centroid_hz": centroid,
        "onset": onset,
        "model_label": None,
        "model_score": raw_score,
        "score_semantics": "uncalibrated_raw_score" if raw_score is not None else "not_scored",
        "raw_clip_id": None,
        "origin_unknown": True,
        "site_id": context.get("site_id"),
        "limitations": limitations,
        "source_mode": context.get("source_mode", "unavailable"),
        "possible_self_noise": bool(
            context.get("solenoid_commanded") and label == "knock"
        ),
        "unit_note": "dBFS is digital full scale, not dB SPL",
    }
