def measured_points(points: list[dict]) -> list[dict]:
    return [point for point in points if point.get("interpolated") is False]


def interpolate_markers(points: list[dict]) -> list[dict]:
    """Optional view. Every synthetic marker is explicitly interpolated."""
    if len(points) < 2:
        return []
    synthetic = []
    for index, point in enumerate(points[:-1]):
        nxt = points[index + 1]
        if point.get("x_cm") is None or nxt.get("x_cm") is None:
            continue
        if point.get("score") is None or nxt.get("score") is None:
            continue
        synthetic.append(
            {
                "point_id": f"interp_{point['point_id']}_{nxt['point_id']}",
                "x_cm": (point["x_cm"] + nxt["x_cm"]) / 2,
                "y_cm": (point["y_cm"] + nxt["y_cm"]) / 2,
                "score": (point["score"] + nxt["score"]) / 2,
                "score_semantics": "uncalibrated_heuristic",
                "interpolated": True,
                "sample_count": 0,
                "method": "midpoint_interpolation",
                "source_mode": point.get("source_mode", "unavailable"),
                "quality": "interpolated",
                "evidence_event_ids": [],
            }
        )
    return synthetic
