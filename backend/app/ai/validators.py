ALLOWED_RECOMMENDATIONS = {
    "stop",
    "rescan_at_point",
    "capture",
    "settle_and_listen",
    "needs_operator",
}
FORBIDDEN_KEYS = {
    "voltage",
    "pwm",
    "pin",
    "motor_speed",
    "gpio",
    "micro_displacement_mm",
    "target_angle_deg",
    "probability",
}


def validate_reasoning(
    payload: object,
    known_event_ids: set[str],
    known_points: set[str],
) -> tuple[dict | None, str | None]:
    if not isinstance(payload, dict):
        return None, "invalid_json_shape"
    try:
        _reject_forbidden(payload)
    except ValueError as exc:
        return None, str(exc)

    event_ids = payload.get("event_ids")
    hypotheses = payload.get("hypotheses")
    summary = payload.get("summary")
    recommendation = payload.get("recommendation")
    unknowns = payload.get("unknowns")
    if not isinstance(event_ids, list) or not all(isinstance(item, str) for item in event_ids):
        return None, "invalid_event_ids"
    if not set(event_ids) <= known_event_ids:
        return None, "unknown_event_id"
    if not isinstance(hypotheses, list) or not hypotheses:
        return None, "invalid_hypotheses"
    if not isinstance(summary, str) or not summary.strip():
        return None, "invalid_summary"
    if not isinstance(unknowns, list):
        return None, "invalid_unknowns"
    if not isinstance(recommendation, dict):
        return None, "invalid_recommendation"

    cleaned_hypotheses = []
    for hypothesis in hypotheses:
        if not isinstance(hypothesis, dict):
            return None, "invalid_hypothesis"
        label = hypothesis.get("label")
        score = hypothesis.get("score")
        evidence = hypothesis.get("evidence_event_ids")
        limitations = hypothesis.get("limitations")
        if not isinstance(label, str) or not label:
            return None, "invalid_hypothesis_label"
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            return None, "invalid_score"
        if not 0 <= float(score) <= 1:
            return None, "score_out_of_range"
        if not isinstance(evidence, list) or not set(evidence) <= known_event_ids:
            return None, "hypothesis_event_mismatch"
        if not isinstance(limitations, list):
            return None, "invalid_limitations"
        cleaned_hypotheses.append(
            {
                "label": label,
                "score": float(score),
                "evidence_event_ids": evidence,
                "limitations": limitations,
            }
        )

    recommendation_type = recommendation.get("type")
    if recommendation_type not in ALLOWED_RECOMMENDATIONS:
        return None, "recommendation_not_allowed"
    if recommendation.get("requires_approval") is not True:
        return None, "approval_required"
    point_id = recommendation.get("point_id")
    if point_id is not None and point_id not in known_points:
        return None, "unknown_point_id"

    return {
        "event_ids": event_ids,
        "hypotheses": cleaned_hypotheses,
        "summary": summary.strip(),
        "recommendation": {
            "type": recommendation_type,
            "point_id": point_id,
            "requires_approval": True,
        },
        "unknowns": unknowns,
        "score_semantics": "model_assessment",
    }, None


def _reject_forbidden(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden_key:{key}")
            _reject_forbidden(item)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden(item)
