import io
import zipfile

from fastapi.testclient import TestClient

from app.config.geometry import search_lattice
from app.services.sim_run import advance_run, start_run
from app.state import get_state
from main import app

client = TestClient(app)


def test_run_publishes_scripted_cases_and_media() -> None:
    started = start_run(schedule=False)
    assert started["mode"] == "SIMULATION"
    seen = []
    phases: set[str] = set()
    state = get_state()
    while state.run_active:
        point_id = advance_run()
        phases.add(get_state().phase)
        if point_id:
            seen.append(point_id)
        state = get_state()
    route = search_lattice()
    assert [cell["id"] for cell in route] == [
        "r1c1", "r1c2", "r1c3",
        "r2c3", "r2c2", "r2c1",
        "r3c1", "r3c2", "r3c3",
    ]
    assert route[0]["border_cm"] > route[1]["border_cm"] > route[2]["border_cm"]
    assert route[2]["border_cm"] < 20
    assert route[5]["border_cm"] < 20
    assert seen == [cell["id"] for cell in route for _ in (0, 1)]
    assert "SIGNS" in phases
    assert "VITALS" in phases
    assert "TURN" in phases
    assert state.phase == "COMPLETE"
    quiet = next(point for point in state.heatmap if point["point_id"] == "r1c1")
    assert quiet["readings"]["radar_presence"] is False
    assert quiet["readings"]["sound"] in {"ambient", "silence"}
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
    near = client.get("/api/simulation/camera.png?point=A_NEAR")
    assert near.status_code == 200
    assert near.content.startswith(b"\x89PNG")
    scores = {point["point_id"]: point for point in state.heatmap}
    assert scores["A_NEAR"]["method"] == "cell_readings"
    assert scores["A_NEAR"]["readings"]["sound"] == "knock"
    assert scores["A_NEAR"]["score"] > scores["A_FAR"]["score"] > scores["C_FAR"]["score"]
    assert audio.status_code == 200
    assert audio.content.startswith(b"RIFF")
    assert len(state.acoustic_waveform) > 8
    assert max(state.acoustic_waveform) != min(state.acoustic_waveform)
    assert len(state.piezo_waveform) > 8
    assert state.rover_trace["left"]
    assert state.rover_trace["right"]
    assert state.ultrasonic["echo_x_cm"] is not None
    snapshot = client.get("/api/operations/snapshot").json()
    assert snapshot["acoustic_waveform"]
    assert snapshot["piezo_waveform"]
    assert snapshot["rover_trace"]["source_mode"] == "simulation"
    assert len(snapshot["scan_route"]) == 9
    assert snapshot["scan_route"][2]["border_cm"] < 20


def test_simulation_export_includes_media_without_a_token() -> None:
    start_run(schedule=False)
    advance_run()
    first = search_lattice()[0]["id"]
    trial_id = get_state().trial_id
    response = client.get(f"/api/trials/{trial_id}/export?format=zip")
    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = archive.namelist()
    assert f"camera/{first}.png" in names
    assert f"audio/{first}.wav" in names
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
