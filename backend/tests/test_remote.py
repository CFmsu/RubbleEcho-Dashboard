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
