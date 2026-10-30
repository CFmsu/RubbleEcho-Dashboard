from app.drivers.motor_link import send_cell, transmit
from app.services import grid_route, pi_link
from app.services.rover_track import apply_rover_line
from app.state import get_state


def test_a_drive_command_waits_for_the_pi_when_the_uno_is_not_on_the_laptop(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr("app.drivers.motor_link.motor_port", lambda: None)
    result = transmit("A")
    assert result["sent"] is True
    assert result["port"] == "pi"
    assert pi_link.take_commands() == ["A"]
    assert get_state().motor_tracking is True


def test_the_next_square_is_queued_for_the_pi(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr("app.drivers.motor_link.motor_port", lambda: None)
    import app.services.rover_track as rover_track

    rover_track._cells_ok = True
    result = send_cell("r2c1")
    assert result["reason"] == "queued"
    assert pi_link.take_commands() == ["Cr2c1\n"]


def test_uno_lines_from_the_pi_open_the_sweep() -> None:
    applied = pi_link.accept_lines(
        [
            "Ready: F B L R S A | Speed 0-9",
            'ACK {"device":"arduino_uno","status":"arrived","cell":"r1c1","heading":0}',
        ]
    )
    assert applied == 1
    assert grid_route.sweep_status()["ready"] is True
    assert apply_rover_line("Ready: F B L R S A | Speed 0-9") is False
