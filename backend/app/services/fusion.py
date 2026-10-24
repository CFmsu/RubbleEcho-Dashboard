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
        if acoustic_class == "knock":
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
