def calibration_report(
    marker_count: int,
    rms_px: float | None,
    threshold_px: float = 2.0,
) -> dict:
    if marker_count < 4:
        return _report(False, False, "insufficient_markers", marker_count, rms_px)
    if rms_px is None:
        return _report(False, False, "reprojection_error_missing", marker_count, None)
    if rms_px > threshold_px:
        return _report(False, False, "bad_reprojection", marker_count, rms_px)
    return _report(
        True,
        False,
        "camera_to_rover_offset_unmeasured",
        marker_count,
        rms_px,
    )


def _report(
    homography_valid: bool,
    pose_valid: bool,
    reason: str,
    marker_count: int,
    rms_px: float | None,
) -> dict:
    return {
        "homography_valid": homography_valid,
        "pose_valid": pose_valid,
        "reason": reason,
        "marker_count": marker_count,
        "rms_px": rms_px,
        "pose_quality": "unavailable" if not pose_valid else "offset_applied",
    }
