from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_live_snapshot_stays_disconnected_without_devices() -> None:
    body = client.get("/api/operations/snapshot").json()
    assert body["version"] == "1"
    assert body["badge"] == "DISCONNECTED"
    assert body["mode"] == "unavailable"
    assert body["system_live"] is False
    assert body["nvidia_online"] is False
    assert body["ai"]["nvidia_online"] is False
    assert body["radar"] is None
    assert body["ultrasonic"] is None
    assert body["acoustic"]["source_mode"] == "live"
    assert body["acoustic"]["class"]
    assert body["piezo"] is None
    assert body["pose"] is None
    assert body["streaming_camera_count"] == 0
    assert body["camera_count"] == 1
    assert body["cameras"][0]["camera_id"] == "camera_top"
    assert body["solenoid"]["state"] == "DISARMED"
    assert body["solenoid"]["output_energized"] is False
    assert body["ai"]["status"] == "NOT_CONFIGURED"
    assert "api_key" not in body
    assert "active_box" not in body


def test_health_route_shape_is_unchanged() -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_estop_does_not_require_a_token_or_energize_output() -> None:
    body = client.post("/api/mission/estop").json()
    assert body["safety_state"] == "ESTOP"
    assert body["output_energized"] is False


def test_missing_trial_export_is_not_a_dataset(auth_header: dict[str, str]) -> None:
    missing = client.get("/api/trials/not-a-trial/export", headers=auth_header)
    assert missing.status_code == 404
