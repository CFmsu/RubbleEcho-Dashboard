import pytest
from fastapi.testclient import TestClient

from main import app
from simulation import confidence_at

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_mission() -> None:
    client.post("/api/mission/reset")
    yield
    client.post("/api/mission/reset")


def test_health() -> None:
    response = client.get("/api/health")
    scenarios = client.get("/api/scenarios").json()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert [item["id"] for item in scenarios] == [
        "earthquake", "flood", "collapse"
    ]
    assert all(
        {"id", "label", "width", "height", "description"} <= item.keys()
        for item in scenarios
    )


def test_demo_is_repeatable() -> None:
    client.post("/api/mission/demo", json={"scenario": "collapse"})
    first = None
    for _ in range(20):
        first = client.post("/api/mission/step").json()

    client.post("/api/mission/demo", json={"scenario": "collapse"})
    second = None
    for _ in range(20):
        second = client.post("/api/mission/step").json()

    assert first is not None
    assert second is not None
    assert first["mission"]["status"] == "DONE"
    assert first["probes"] == second["probes"]

    client.post("/api/mission/start", json={"scenario": "earthquake"})
    with client.websocket_connect("/ws/telemetry") as socket:
        first_frame = socket.receive_json()
        second_frame = socket.receive_json()

    assert set(first_frame) == {"mission", "robot", "probes", "events"}
    assert first_frame["mission"]["status"] == "ACTIVE"
    assert second_frame["mission"]["phase"] != first_frame["mission"]["phase"]
    assert "source" not in str(first_frame)
    assert "source" not in str(second_frame)


def test_confidence_rises_near_source() -> None:
    source = (6, 6)

    near = confidence_at((5, 6), source, noise=0.0)
    far = confidence_at((0, 0), source, noise=0.0)

    assert near > far


def test_pause_stops_new_probes() -> None:
    client.post("/api/mission/start", json={"scenario": "earthquake"})
    for _ in range(3):
        client.post("/api/mission/step")

    paused = client.post("/api/mission/pause").json()
    count_before = paused["mission"]["probe_count"]
    for _ in range(8):
        paused = client.post("/api/mission/step").json()

    assert paused["mission"]["status"] == "PAUSED"
    assert paused["mission"]["probe_count"] == count_before


def test_reset_returns_to_standby() -> None:
    client.post("/api/mission/start", json={"scenario": "flood"})
    for _ in range(3):
        client.post("/api/mission/step")

    reset = client.post("/api/mission/reset").json()

    assert reset["mission"]["status"] == "STANDBY"
    assert reset["mission"]["probe_count"] == 0
    assert reset["probes"] == []
    assert reset["events"] == []