import os

from app.drivers.solenoid import SolenoidController
from app.drivers.solenoid_link import solenoid_port, transmit


class _Port:
    def __init__(self, device: str, description: str, hwid: str) -> None:
        self.device = device
        self.description = description
        self.hwid = hwid


def test_sketch_timings_match_the_arduino_knock() -> None:
    controller = SolenoidController()
    status = controller.public_status()
    assert status["pattern"] == {
        "pin": "A0",
        "on_ms": 200,
        "off_ms": 200,
        "taps": 3,
        "interval_ms": 5000,
    }
    controller.arm(True)
    accepted = controller.request_pulse(200, False, 0, True)
    assert accepted["accepted"] is True
    assert accepted["output_energized"] is False


def test_radar_port_is_not_used_for_the_solenoid() -> None:
    ports = [
        _Port("COM9", "USB Serial Device", "USB VID:PID=303A:1001"),
        _Port("COM6", "USB-SERIAL CH340", "USB VID:PID=1A86:7523"),
    ]
    assert solenoid_port(ports) == "COM6"


def test_knock_command_is_the_line_written_to_the_board(monkeypatch) -> None:
    monkeypatch.setenv("RUBBLEECHO_SOLENOID_PORT", "COM6")
    seen: list[tuple[str, str]] = []
    result = transmit("KNOCK", write=lambda port, command: seen.append((port, command)))
    assert result["sent"] is True
    assert seen == [("COM6", "KNOCK")]
    monkeypatch.delenv("RUBBLEECHO_SOLENOID_PORT", raising=False)
    os.environ.pop("RUBBLEECHO_SOLENOID_PORT", None)
