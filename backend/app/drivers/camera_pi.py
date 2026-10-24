from app.config.settings import probe_cameras

CAMERAS = [
    {
        "camera_id": "camera_top",
        "name": "Camera",
        "panoramic_360": False,
    },
]


def _blank(camera: dict, state: str, error: str) -> dict:
    return {
        **camera,
        "state": state,
        "source_mode": "unavailable",
        "fps": None,
        "width": None,
        "height": None,
        "last_frame_utc": None,
        "last_frame_age_ms": None,
        "error": error,
        "frame_available": False,
    }


def default_cameras() -> list[dict]:
    return [_blank(camera, "disconnected", "not_enumerated") for camera in CAMERAS]


def camera_states() -> list[dict]:
    if not probe_cameras():
        return [
            _blank(camera, "disconnected", "not_enumerated")
            for camera in CAMERAS
        ]

    try:
        import cv2
    except ImportError:
        return [
            _blank(camera, "error", "opencv_not_installed")
            for camera in CAMERAS
        ]

    states = []
    for index, camera in enumerate(CAMERAS):
        capture = cv2.VideoCapture(index)
        opened = bool(capture.isOpened())
        if opened:
            ok, _frame = capture.read()
            opened = bool(ok)
        capture.release()
        if not opened:
            states.append(_blank(camera, "disconnected", "open_failed"))
            continue
        states.append(
            {
                **camera,
                "state": "connected",
                "source_mode": "live",
                "fps": None,
                "width": None,
                "height": None,
                "last_frame_utc": None,
                "last_frame_age_ms": None,
                "error": None,
                "frame_available": False,
            }
        )
    return states


def streaming_count(cameras: list[dict]) -> int:
    return sum(
        1
        for camera in cameras
        if camera["state"] == "connected"
        and camera["source_mode"] == "live"
        and camera["frame_available"]
    )


def find_camera(camera_id: str, cameras: list[dict] | None = None) -> dict | None:
    for camera in cameras or camera_states():
        if camera["camera_id"] == camera_id:
            return camera
    return None
