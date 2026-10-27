import os

from app.drivers.motor_link import motor_port, transmit


class _Port:
    def __init__(self, device: str, description: str, hwid: str) -> None:
        self.device = device
        self.description = description
        self.hwid = hwid


def test_radar_port_is_not_the_rover() -> None:
    ports = [
        _Port("COM9", "USB Serial Device", "USB VID:PID=303A:1001"),
        _Port("COM4", "USB-SERIAL CH340", "USB VID:PID=1A86:7523"),
    ]
    assert motor_port(ports) == "COM4"


def test_auto_command_is_the_single_character_a(monkeypatch) -> None:
    monkeypatch.setenv("RUBBLEECHO_MOTOR_PORT", "COM4")
    seen: list[tuple[str, str]] = []
    result = transmit("A", write=lambda port, command: seen.append((port, command)))
    assert result["sent"] is True
    assert seen == [("COM4", "A")]
    monkeypatch.delenv("RUBBLEECHO_MOTOR_PORT", raising=False)
    os.environ.pop("RUBBLEECHO_MOTOR_PORT", None)
