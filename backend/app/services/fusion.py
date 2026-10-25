def gcc_phat_delays(mics: object, sample_rate: float = 16000.0, max_lag: int = 3) -> dict:
    """Sub-sample GCC-PHAT across 4 mics.

    At 16 kHz one sample is 62.5 µs. A ~5 cm array limits the direct path to
    about 2.3 samples, so the lag search is clamped to ±max_lag samples.
    Positive delay means that channel's waveform arrives later than channel 0.
    """
    import numpy as np

    data = np.asarray(mics, dtype=np.float64)
    if data.ndim != 2 or data.shape[1] < 2 or data.shape[0] < 32:
        return {
            "valid": False,
            "reason": "need_a_multichannel_onset_window",
            "delays_samples": [],
            "delays_us": [],
            "summary": "no onset window",
        }
    delays = [0.0]
    for channel in range(1, data.shape[1]):
        delays.append(_gcc_phat_lag(data[:, channel], data[:, 0], max_lag))
    closure = _closure_error(data, delays, max_lag)
    edge = any(abs(value) >= max_lag - 0.05 and channel > 0 for channel, value in enumerate(delays))
    valid = closure <= 0.75 and not edge
    microseconds = [value * 1e6 / sample_rate for value in delays]
    rendered = ", ".join(
        f"ch{index} {value:+.0f} us" for index, value in enumerate(microseconds)
    )
    summary = f"{rendered}; closure {closure:.2f} samples"
    if not valid:
        summary = f"unresolved ({summary})"
    return {
        "valid": valid,
        "reason": None if valid else "lag_outside_array_or_pairs_disagree",
        "reference_channel": 0,
        "max_lag_samples": max_lag,
        "delays_samples": [round(value, 3) for value in delays],
        "delays_us": [round(value, 1) for value in microseconds],
        "closure_error_samples": round(closure, 3),
        "summary": summary,
        "bearing": None,
        "limit": "array delay only; rubble multipath and a missing mic survey block a bearing",
    }


def _gcc_phat_lag(sig: object, ref: object, max_lag: int) -> float:
    import numpy as np

    left = np.asarray(sig, dtype=np.float64)
    right = np.asarray(ref, dtype=np.float64)
    nfft = 1 << int(left.size + right.size - 1).bit_length()
    cross = np.fft.rfft(left, n=nfft) * np.conj(np.fft.rfft(right, n=nfft))
    cross /= np.abs(cross) + 1e-12
    correlation = np.fft.irfft(cross, n=nfft)
    lags = np.arange(-max_lag, max_lag + 1)
    values = np.array([correlation[int(lag) % nfft] for lag in lags])
    peak = int(np.argmax(values))
    delta = 0.0
    if 0 < peak < values.size - 1:
        y0, y1, y2 = float(values[peak - 1]), float(values[peak]), float(values[peak + 1])
        denom = y0 - 2.0 * y1 + y2
        if abs(denom) > 1e-12:
            delta = 0.5 * (y0 - y2) / denom
            delta = max(-0.5, min(0.5, delta))
    return float(lags[peak] + delta)


def _closure_error(data: object, delays_vs_ref: list[float], max_lag: int) -> float:
    """Each pair's GCC lag should match the difference of the reference delays."""
    import numpy as np

    errors = []
    channels = data.shape[1]
    for first in range(channels):
        for second in range(first + 1, channels):
            predicted = delays_vs_ref[first] - delays_vs_ref[second]
            if abs(predicted) > max_lag + 0.5:
                errors.append(abs(predicted))
                continue
            measured = _gcc_phat_lag(data[:, first], data[:, second], max_lag)
            errors.append(abs(measured - predicted))
    if not errors:
        return 0.0
    return float(np.max(errors))


def window_score(
    acoustic_class: str | None,
    piezo_peak: float | None,
    coincident: bool,
) -> float | None:
    """Uncalibrated impulse score. Missing modalities are omitted, not treated as zero.

    Radar is intentionally not an input. Through-sand vital signs are not a claim.
    """
    parts: list[float] = []
    if acoustic_class is not None:
        if acoustic_class in {"knock", "periodic_tapping"}:
            parts.append(1.0)
        elif acoustic_class == "scratch/scrape":
            parts.append(0.55)
        else:
            parts.append(0.0)
    if piezo_peak is not None:
        parts.append(min(1.0, float(piezo_peak) / 1000.0))
    if not parts:
        return None
    if coincident and acoustic_class == "knock":
        parts.append(1.0)
    return sum(parts) / len(parts)


def fuse_sites(windows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for window in windows:
        site_id = window.get("site_id")
        if not site_id:
            continue
        grouped.setdefault(site_id, []).append(window)

    points = []
    for site_id, site_windows in grouped.items():
        scores = []
        evidence_ids = []
        for window in site_windows:
            score = window.get("score")
            if score is not None:
                scores.append(score)
            if window.get("evidence_event_ids"):
                evidence_ids.extend(window["evidence_event_ids"])
            elif window.get("event_id"):
                evidence_ids.append(window["event_id"])
        if not scores:
            continue
        first = site_windows[0]
        points.append(
            {
                "point_id": site_id,
                "x_cm": first.get("x_cm"),
                "y_cm": first.get("y_cm"),
                "score": max(scores),
                "score_semantics": "uncalibrated_heuristic",
                "interpolated": False,
                "sample_count": len(site_windows),
                "method": "max_impulse_coincidence_v1",
                "source_mode": first.get("source_mode", "unavailable"),
                "quality": "unverified",
                "evidence_event_ids": evidence_ids,
                "coverage": {
                    "acoustic": "present" if any(item.get("acoustic_class") for item in site_windows) else "unknown",
                    "piezo": "present" if any(item.get("piezo_peak") is not None for item in site_windows) else "unknown",
                    "radar_burial_claim": "excluded",
                },
            }
        )
    return points


def local_assessment(events: list[dict], heatmap: list[dict]) -> dict:
    knock_ids = [
        event["event_id"]
        for event in events
        if event.get("acoustic_class") == "knock"
    ]
    site_id = None
    for event in events:
        if event.get("acoustic_class") == "knock" and event.get("site_id"):
            site_id = event["site_id"]
            break

    hypotheses = []
    if knock_ids:
        hypotheses.append(
            {
                "label": "buried_mechanical_knock_candidate",
                "score": None,
                "evidence_event_ids": knock_ids[:8],
                "limitations": [
                    "heuristic score is uncalibrated",
                    "reference piezo is not in the inventory",
                    "open-air sound is not evidence the impulse came from a buried box",
                ],
            }
        )
    hypotheses.append(
        {
            "label": "no_reliable_evidence" if not knock_ids else "no_reliable_buried_localization",
            "score": None,
            "evidence_event_ids": knock_ids[:8],
            "limitations": [
                "radar through-sand vital signs are not validated",
                "a louder point is not a located person",
            ],
        }
    )
    if knock_ids:
        summary = (
            "A digital impulse was measured. This local readout is not a Nebius or NVIDIA result, "
            "and it does not locate a person."
        )
    else:
        summary = "No reliable impulse evidence is in the current trial."
    return {
        "event_ids": knock_ids[:8],
        "hypotheses": hypotheses,
        "summary": summary,
        "recommendation": {
            "type": "needs_operator",
            "point_id": site_id,
            "requires_approval": True,
            "detail": (
                "Settle, record a silence baseline, and repeat the labeled knock or scratch trial "
                "at the point that produced the impulse."
                if site_id
                else "Collect a labeled silence baseline before treating any card as evidence."
            ),
        },
        "unknowns": [
            "radar through-sand validity",
            "microphone coupling through plywood and sand",
        ],
        "provider": "deterministic_safety_fallback",
        "model_id": None,
        "latency_ms": None,
        "validation_status": "local_only",
        "score_semantics": "not_a_model_score",
        "nvidia_online": False,
        "live_call": False,
        "heatmap_point_count": len(heatmap),
    }
