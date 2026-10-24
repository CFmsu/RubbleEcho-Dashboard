def aruco_backend_status() -> dict:
    try:
        import cv2
    except ImportError:
        return {
            "available": False,
            "reason": "opencv_not_installed",
            "status": "NEEDS_HARDWARE_VERIFICATION",
        }
    if not hasattr(cv2, "aruco"):
        return {
            "available": False,
            "reason": "cv2_aruco_missing_install_opencv_contrib_not_both_opencv_packages",
            "status": "NEEDS_HARDWARE_VERIFICATION",
        }
    return {
        "available": True,
        "reason": "library_present_no_frame_or_marker_survey",
        "status": "NEEDS_HARDWARE_VERIFICATION",
        "markers_detected": None,
    }
