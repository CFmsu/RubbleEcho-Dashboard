import json

from fastapi.testclient import TestClient

from core.mission_controller import MissionController
from main import app
from models.mission import SimulationConfig
from reasoning.sensor_fusion import fuse
from simulation.acoustic import generate_audio
from simulation.environment import Environment
from simulation.piezo import generate_vibration
from simulation.survivor import observe


def test_environment_is_deterministic():
    config = SimulationConfig(seed=42, survivor_x=7.2, survivor_y=6.4)
    first = Environment(config)
    second = Environment(config)
    assert first.debris == second.debris
    assert first.distance_to_survivor(1, 1) == second.distance_to_survivor(1, 1)


def test_same_seed_same_observation():
    config = SimulationConfig(seed=42, width=12, height=12, survivor_x=7.2, survivor_y=6.4)
    first = observe(Environment(config), 5.5, 4.5, config)
    second = observe(Environment(config), 5.5, 4.5, config)
    assert first.model_dump() == second.model_dump()


def test_response_stronger_near_source():
    config = SimulationConfig(seed=42, noise_level=0.0, response_probability=1, sensor_reliability=1)
    env = Environment(config)
    near = observe(env, config.survivor_x, config.survivor_y, config)
    far = observe(env, 0.6, 0.6, config)
    assert fuse(near).combined > fuse(far).combined


def test_sensor_waveforms_change_with_state():
    import random

    quiet = generate_audio("NO_RESPONSE", 0.1, random.Random(1))
    taps = generate_audio("CONFIRMED_RESPONSE", 0.9, random.Random(1))
    assert taps.energy > quiet.energy
    weak = generate_vibration(0.2, 0.1, random.Random(2))
    strong = generate_vibration(0.9, 0.8, random.Random(2))
    assert strong.peak_amplitude >= weak.peak_amplitude


def test_mission_start_pause_reset():
    mission = MissionController()
    assert mission.status == "IDLE"
    mission.start()
    assert mission.status == "ACTIVE"
    assert mission.phase == "NAVIGATING"
    mission.pause()
    assert mission.status == "PAUSED"
    held = mission.sim_time
    mission.tick(3)
    assert mission.sim_time == held
    mission.resume()
    mission.tick(0.2)
    assert mission.sim_time > held
    mission.reset()
    assert mission.status == "IDLE"
    assert mission.probes == []


def test_step_advances_phase():
    mission = MissionController()
    mission.start()
    mission.step()
    assert mission.phase == "CONTACT"


def test_demo_reaches_candidate_location():
    mission = MissionController()
    mission.start(demo=True)
    for _ in range(500):
        if mission.status == "COMPLETE":
            break
        mission.tick(3)
    assert mission.outcome == "SURVIVOR LOCATION IDENTIFIED"
    assert mission.candidate is not None
    assert mission.highest >= 0.8
    assert mission.candidate.status == "Awaiting Rescue Team Verification"
    assert abs(mission.candidate.x - 7.2) < 0.4
    assert abs(mission.candidate.y - 6.4) < 0.4
    assert len(mission.probes) == 5


def test_telemetry_does_not_publish_ground_truth():
    mission = MissionController()
    mission.start(demo=True)
    payload = json.dumps(mission.snapshot().model_dump())
    assert "survivor_x" not in payload
    assert "survivor_y" not in payload


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["mode"] == "simulation"
