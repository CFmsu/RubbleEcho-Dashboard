from app.vision.calibration import calibration_report
from app.vision.homography import apply_homography


def rover_pose_from_pixel(
    homography: list[list[float]] | None,
    pixel: tuple[float, float],
    marker_count: int,
    rms_px: float | None,
    offset_cm: tuple[float, float] | None = None,
) -> dict:
    report = calibration_report(marker_count, rms_px)
    if homography is None or not report["homography_valid"]:
        return {**report, "x_cm": None, "y_cm": None, "pose_valid": False, "source": "aruco"}
    mapped = apply_homography(homography, pixel[0], pixel[1])
    if mapped is None:
        return {
            **report,
            "homography_valid": False,
            "pose_valid": False,
            "reason": "homography_degenerate",
            "x_cm": None,
            "y_cm": None,
            "source": "aruco",
        }
    if offset_cm is None:
        return {
            **report,
            "pose_valid": False,
            "reason": "camera_to_rover_offset_unmeasured",
            "x_cm": None,
            "y_cm": None,
            "plane_x_cm": mapped[0],
            "plane_y_cm": mapped[1],
            "source": "aruco",
        }
    return {
        **report,
        "homography_valid": True,
        "pose_valid": True,
        "reason": "ok",
        "pose_quality": "offset_applied",
        "x_cm": mapped[0] + offset_cm[0],
        "y_cm": mapped[1] + offset_cm[1],
        "source": "aruco",
    }
