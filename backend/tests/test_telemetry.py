from fastapi.testclient import TestClient

from app.vision.homography import apply_homography, solve_homography
from app.vision.pose import rover_pose_from_pixel
from main import app

client = TestClient(app)


def test_operations_socket_uses_a_separate_contract() -> None:
    with client.websocket_connect("/ws/operations") as socket:
        frame = socket.receive_json()
    assert frame["badge"] == "DISCONNECTED"
    assert frame["system_live"] is False
    assert "mission" not in frame
    assert "active_box" not in frame


def test_cameras_are_not_marked_streaming() -> None:
    body = client.get("/api/cameras").json()
    assert body["camera_count"] == 3
    assert body["streaming_camera_count"] == 0
    assert all(camera["state"] == "disconnected" for camera in body["cameras"])
    assert all(camera["panoramic_360"] is False for camera in body["cameras"])
    missing = client.get("/api/camera/not-a-camera/latest")
    assert missing.status_code == 404


def test_homography_and_unmeasured_offset() -> None:
    homography = solve_homography(
        [(0, 0), (1, 0), (0, 1), (1, 1)],
        [(1, 4), (3, 4), (1, 7), (3, 7)],
    )
    assert homography is not None
    mapped = apply_homography(homography, 0.5, 0.5)
    assert mapped is not None
    assert abs(mapped[0] - 2) < 1e-6
    assert abs(mapped[1] - 5.5) < 1e-6
    unresolved = rover_pose_from_pixel(homography, (0.5, 0.5), 4, 0.2, None)
    assert unresolved["homography_valid"] is True
    assert unresolved["pose_valid"] is False
    assert unresolved["reason"] == "camera_to_rover_offset_unmeasured"
    insufficient = rover_pose_from_pixel(homography, (0.5, 0.5), 3, 0.2, (0, 0))
    assert insufficient["reason"] == "insufficient_markers"
    poor = rover_pose_from_pixel(homography, (0.5, 0.5), 5, 4.0, (1, 2))
    assert poor["reason"] == "bad_reprojection"
    posed = rover_pose_from_pixel(homography, (0.5, 0.5), 4, 0.2, (1, 2))
    assert posed["pose_valid"] is True
    assert abs(posed["x_cm"] - 3) < 1e-6
    assert abs(posed["y_cm"] - 7.5) < 1e-6
