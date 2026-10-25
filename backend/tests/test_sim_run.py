import io
import zipfile

from fastapi.testclient import TestClient

from app.services.sim_run import advance_run, start_run
from app.state import get_state
from main import app

client = TestClient(app)


def test_run_publishes_scripted_cases_and_media() -> None:
    started = start_run(schedule=False)
    assert started["mode"] == "SIMULATION"
    seen = []
    state = get_state()
    while state.run_active:
        point_id = advance_run()
        if point_id:
            seen.append(point_id)
        state = get_state()
    assert seen == ["A_NEAR", "A_FAR", "B_NEAR", "B_FAR", "C_NEAR", "C_FAR"]
    assert state.phase == "COMPLETE"
    assert state.radar["case_name"] == "control_quiet"
    assert state.radar["heart_rate_bpm"] == 0.0
    assert state.radar["breath_rate_bpm"] == 0.0
    assert state.radar["num_targets"] == 0
    assert state.ultrasonic["distance_cm"] == 44.2
    assert state.ultrasonic["source_mode"] == "simulation"
    assert state.acoustic["source_mode"] == "simulation"
    assert state.piezo["source_mode"] == "simulation"
    assert state.cameras[0]["image_url"].startswith("/api/simulation/camera.png")
    assert state.cameras[0]["source_mode"] == "simulation"
    assert any(device["state"] == "simulated" for device in state.devices)
    assert all(device["source_mode"] != "live" for device in state.devices)
    assert state.solenoid.public_status()["output_energized"] is False
    frame = client.get("/api/simulation/camera.png")
    audio = client.get("/api/simulation/audio.wav")
    assert frame.status_code == 200
    assert frame.content.startswith(b"\x89PNG")
    assert audio.status_code == 200
    assert audio.content.startswith(b"RIFF")


def test_simulation_export_includes_media_without_a_token() -> None:
    start_run(schedule=False)
    advance_run()
    trial_id = get_state().trial_id
    response = client.get(f"/api/trials/{trial_id}/export?format=zip")
    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = archive.namelist()
    assert "camera/A_NEAR.png" in names
    assert "audio/A_NEAR.wav" in names
    assert "measurements.csv" in names
    assert b"NEBIUS_API_KEY" not in response.content


def test_halt_returns_the_console_to_idle() -> None:
    start_run(schedule=False)
    advance_run()
    body = client.post("/api/mission/halt").json()
    assert body["mission_phase"] == "IDLE"
    state = get_state()
    assert state.run_active is False
    assert state.mode == "unavailable"
    assert state.heatmap == []
    assert client.get("/api/simulation/camera.png").status_code == 404


def test_stop_on_an_idle_console_stays_idle() -> None:
    body = client.post("/api/mission/halt").json()
    assert body["mission_phase"] == "IDLE"
    assert "Already idle" in body["message"]
    assert get_state().events == []


def test_header_stop_ends_the_scripted_walk() -> None:
    start_run(schedule=False)
    advance_run()
    body = client.post("/api/mission/estop").json()
    assert body["mission_phase"] == "ESTOP"
    assert body["output_energized"] is False
    assert get_state().run_active is False
