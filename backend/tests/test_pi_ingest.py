import base64
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_scripted_demo_does_not_drive_and_blocks_pi_samples() -> None:
    started = client.post("/api/mission/run")
    assert started.status_code == 200
    assert started.json()["rover"]["reason"] == "simulation_does_not_drive"
    blocked = client.post("/api/pi/ingest", json={"radar": {"human_presence": True, "breath_rate_bpm": 12}})
    assert blocked.status_code == 409


def test_motion_requires_authorization_and_pi_samples_are_live() -> None:
    refused = client.post("/api/mission/hardware", json={"authorize_motion": False})
    assert refused.status_code == 403

    opened = client.post("/api/mission/live")
    assert opened.status_code == 200
    assert opened.json()["motion"] == "not_authorized"

    posted = client.post(
        "/api/pi/ingest",
        json={"radar": {"human_presence": True, "breath_rate_bpm": 14.0, "distance_m": 0.4}},
    )
    assert posted.status_code == 200
    snapshot = client.get("/api/operations/snapshot").json()
    assert snapshot["mode"] == "live"
    assert snapshot["radar"]["human_presence"] is True
    assert snapshot["radar"]["source_mode"] == "live"
    pi = next(device for device in snapshot["devices"] if device["device_id"] == "raspberry_pi_4")
    assert pi["state"] == "connected"


def test_reasoned_drop_is_saved_for_the_model() -> None:
    posted = client.post(
        "/api/pi/ingest",
        json={
            "reason": True,
            "ultrasonic": {"distance_cm": 33.5},
            "audio": {"sample_rate": 16000, "samples": [0.0] * 40 + [0.2] * 80},
        },
    )
    assert posted.status_code == 200
    body = posted.json()
    assert "ultrasonic" in body["applied"]
    assert "acoustic" in body["applied"]
    folder = Path(body["folder"])
    assert (folder / "ultrasonic.json").is_file()
    assert (folder / "audio.json").is_file()
    assert (folder / "reasoning.json").is_file()
    assert isinstance(body["reasoning"], dict)
    assert body["reasoning"].get("summary") or body["reasoning"].get("narrative")


def test_a_cell_recording_reaches_the_model_and_the_scope() -> None:
    posted = client.post(
        "/api/pi/ingest",
        json={
            "reason": True,
            "cell": "r1c1",
            "ultrasonic": {"distance_cm": 28},
            "audio": {"sample_rate": 1600, "samples": [0.0] * 20 + [0.6, -0.5, 0.4]},
        },
    )
    assert posted.status_code == 200
    body = posted.json()
    snapshot = client.get("/api/operations/snapshot").json()
    assert snapshot["acoustic_waveform"]
    assert snapshot["ultrasonic"]["distance_cm"] == 28
    assert snapshot["heatmap_points"] == []
    from app.state import get_state

    stored = next(item for item in get_state().cell_captures if item["point_id"] == "r1c1")
    assert stored["readings"]["ultrasonic_cm"] == 28
    assert stored["readings"]["sound_category"]
    assert "nine squares" in body["reasoning"]["summary"]
    folder = Path(body["folder"])
    assert (folder / "r1c1.json").is_file()


def test_camera_stores_only_a_posted_frame(auth_header) -> None:
    missing = client.post("/api/camera/camera_top/capture", headers=auth_header)
    assert missing.status_code == 409
    encoded = base64.b64encode(b"jpeg-bytes").decode("ascii")
    posted = client.post("/api/pi/ingest", json={"camera_id": "camera_top", "camera_jpeg_base64": encoded})
    assert posted.status_code == 200
    latest = client.get("/api/camera/camera_top/latest")
    assert latest.status_code == 200
    assert latest.content == b"jpeg-bytes"
