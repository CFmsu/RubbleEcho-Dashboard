import math


def piezo_features(
    samples: list[float],
    sample_rate_hz: float,
    contact_state: str,
    site_id: str | None,
    clipped: bool = False,
) -> dict:
    if not samples or sample_rate_hz <= 0:
        return {"valid": False, "reason": "no_samples", "unit": "adc_counts"}

    peak = max(abs(value) for value in samples)
    mean_square = sum(value * value for value in samples) / len(samples)
    return {
        "valid": True,
        "rms_adc_counts": math.sqrt(mean_square),
        "peak_adc_counts": peak,
        "sample_rate_hz": sample_rate_hz,
        "contact_state": contact_state,
        "site_id": site_id,
        "clipped": clipped,
        "unit": "adc_counts",
        "acceleration_g": None,
        "correlated_knock_id": None,
        "notes": [
            "adc_counts_are_not_acceleration",
            "full_scale_unverified" if not clipped else "clipping_reported",
        ],
        "source_mode": "unavailable",
    }
