from app.drivers.solenoid import SolenoidController
from app.services.policy import assess_motion, on_link_lost, vet_command
from app.state import get_state
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _clear_context() -> dict:
    return {
        "echo_timeout": False,
        "distance_cm": 80,
        "pose_valid": True,
        "pose_age_ms": 0,
        "heading_deg": 0,
        "encoder_fresh": True,
        "mode": "live",
        "operator_link": True,
        "target_x_cm": 52.5,
        "target_y_cm": 39.5,
    }


def test_motion_hazards_stop() -> None:
    missing = assess_motion({**_clear_context(), "echo_timeout": True, "distance_cm": None})
    assert "missing_echo" in missing["reasons"]
    assert missing["hard_stop"] is True
    assert missing["execute_hardware"] is False

    obstacle = assess_motion({**_clear_context(), "distance_cm": 10})
    assert "obstacle_inside_stop_margin" in obstacle["reasons"]

    stale = assess_motion({**_clear_context(), "pose_age_ms": 5000})
    assert "stale_pose" in stale["reasons"]

    invalid = assess_motion({**_clear_context(), "pose_valid": False})
    assert "invalid_pose" in invalid["reasons"]

    outside = assess_motion({**_clear_context(), "target_x_cm": 1, "target_y_cm": 1})
    assert "out_of_bounds" in outside["reasons"]

    encoders = assess_motion({**_clear_context(), "encoder_fresh": False})
    assert "encoder_timeout" in encoders["reasons"]

    link = on_link_lost("live")
    assert link["safety"] == "ESTOP"
    assert link["disarm"] is True
    assert on_link_lost("replay")["disarm"] is False


def test_duplicate_and_disallowed_commands() -> None:
    seen: set[str] = set()
    rejected = vet_command({"command_id": "c1", "type": "set_pwm"}, _clear_context(), seen)
    assert rejected["hard_stop"] is True
    assert rejected["transmitted"] is False
    first = vet_command(
        {"command_id": "c2", "type": "stop"}, _clear_context(), seen
    )
    assert first["accepted"] is True
    seen.add("c2")
    duplicate = vet_command({"command_id": "c2", "type": "stop"}, _clear_context(), seen)
    assert duplicate["reasons"] == ["duplicate_command"]
    assert duplicate["disarm"] is True


def test_solenoid_never_energizes() -> None:
    controller = SolenoidController()
    assert controller.public_status()["state"] == "DISARMED"
    denied = controller.request_pulse(40, False, 0, True)
    assert denied["reason"] == "disarmed"
    assert controller.arm(True)["output_energized"] is False
    runaway = controller.request_pulse(250, False, 0, True)
    assert runaway["accepted"] is False
    assert runaway["output_energized"] is False
    assert controller.state == "FAULT"

    controller.reset()
    controller.arm(True)
    moving = controller.request_pulse(40, True, 0, True)
    assert moving["reason"] == "rover_moving"
    assert controller.public_status()["physically_confirmed"] is False
    assert controller.note_reference_sensor()["reason"] == "reference_piezo_not_in_inventory"

    controller.reset()
    controller.arm(True)
    assert controller.request_pulse(40, False, 0, True)["reason"] == "accepted_not_energized"
    early = controller.request_pulse(40, False, 100, True)
    assert early["reason"] == "refractory"
    assert controller.request_pulse(40, False, 250, True)["accepted"] is True
    assert controller.request_pulse(40, False, 500, True)["accepted"] is True
    cooled = controller.request_pulse(40, False, 750, True)
    assert cooled["reason"] == "cooldown"
    assert controller.public_status()["output_energized"] is False


def test_estop_endpoint_disarms_without_a_token() -> None:
    state = get_state()
    state.solenoid.arm(True)
    response = client.post("/api/mission/estop")
    assert response.status_code == 200
    body = response.json()
    assert body["safety_state"] == "ESTOP"
    assert body["output_energized"] is False
    assert get_state().solenoid.state == "DISARMED"
