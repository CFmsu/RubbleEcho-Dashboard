from fastapi.testclient import TestClient

from app.drivers.motor_link import transmit
from main import app

client = TestClient(app)


def test_manual_direction_is_sent(monkeypatch) -> None:
    monkeypatch.setenv("RUBBLEECHO_MOTOR_PORT", "COM4")
    seen: list[str] = []
    result = transmit("F", write=lambda _port, command: seen.append(command))
    assert result["sent"] is True
    assert seen == ["F"]
    refused = client.post("/api/remote/drive", json={"command": "A"})
    assert refused.status_code == 400


def test_sensor_off_skips_the_sample_and_a_signal_does_not_drive() -> None:
    off = client.post("/api/remote/sensor", json={"sensor": "radar", "enabled": False})
    assert off.status_code == 200
    posted = client.post("/api/pi/ingest", json={"radar": {"human_presence": True, "breath_rate_bpm": 12}})
    assert posted.status_code == 200
    assert posted.json()["skipped"] == ["radar"]
    snapshot = client.get("/api/operations/snapshot").json()
    assert snapshot["radar"] is None
    assert snapshot["remote"]["drives_itself"] is False
    assert snapshot["remote"]["mode"] == "stopped"


def test_phone_can_drive_and_auto_stays_stopped_until_armed(monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setenv("RUBBLEECHO_MOTOR_PORT", "COM4")
    monkeypatch.setattr(
        "app.services.remote_drive.transmit",
        lambda command: seen.append(command) or {"sent": True, "port": "COM4", "command": command, "reason": "sent"},
    )
    stopped = client.get("/api/remote").json()
    assert stopped["mode"] == "stopped"
    assert stopped["stopped"] is True

    manual = client.post("/api/remote/mode", json={"mode": "manual"})
    assert manual.status_code == 200
    assert manual.json()["mode"] == "manual"
    assert seen == ["S"]

    forward = client.post("/api/remote/drive", json={"command": "F"})
    assert forward.status_code == 200
    assert forward.json()["rover"]["sent"] is True
    assert seen == ["S", "F"]


def test_arm_sends_the_grid_start() -> None:
    armed = client.post("/api/mission/hardware", json={"authorize_motion": True})
    assert armed.status_code == 200
    body = armed.json()
    assert body["motion"] == "authorized"
    assert body["rover"]["command"] == "A"
    forward = client.post("/api/remote/drive", json={"command": "F"})
    assert forward.json()["rover"]["reason"] != "auto_sampling"


def test_posted_audio_is_categorized() -> None:
    samples = [0.0] * 40 + [0.2] * 80
    posted = client.post("/api/pi/ingest", json={"audio": {"sample_rate": 16000, "samples": samples}})
    assert posted.status_code == 200
    assert "acoustic" in posted.json()["applied"]
    heard = client.get("/api/operations/snapshot").json()["acoustic"]
    assert heard["class"] == "scratch/scrape"
    assert heard["sound_category"] == "scrape"
