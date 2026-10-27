import struct

from fastapi.testclient import TestClient

from app.drivers.radar_mr60bha2 import (
    _checksum,
    apply_esphome_line,
    apply_plain_radar_line,
    blank_reading,
    parse_binary_frames,
    parse_radar_line,
    reading_to_observation,
)
from app.services.radar_link import _publish_dummy
from app.state import get_state
from main import app

client = TestClient(app)


def test_esphome_kit_fields_keep_breath_without_a_stability_flag() -> None:
    observation, error = parse_radar_line(
        '{"human_presence":true,"breath_rate_bpm":15,"heart_rate_bpm":70,"num_targets":1,"distance_m":0.8,"illuminance_lx":120,"valid":true}'
    )
    assert error is None
    assert observation is not None
    assert observation["breath_rate_bpm"] == 15
    assert observation["heart_rate_bpm"] == 70
    assert observation["num_targets"] == 1
    assert observation["distance_m"] == 0.8
    assert observation["illuminance_lx"] == 120
    assert observation["target_xy_m"] is None


def test_esphome_log_lines_fill_the_same_observation() -> None:
    reading = blank_reading()
    lines = [
        "[D][binary_sensor:036]: 'Person Information': Sending state ON",
        "[D][sensor:094]: 'Real-time respiratory rate': Sending state 16.00000 breaths/min with 2 decimals of accuracy",
        "[D][sensor:094]: 'Real-time heart rate': Sending state 74.00000 bpm with 2 decimals of accuracy",
        "[D][sensor:094]: 'Distance to detection object': Sending state 0.90000 m with 2 decimals of accuracy",
        "[D][sensor:094]: 'Target number': Sending state 1.00000 with 0 decimals of accuracy",
        "[D][sensor:094]: 'Seeed MR60BHA2 Illuminance': Sending state 180.00000 lx with 1 decimals of accuracy",
    ]
    for line in lines:
        assert apply_esphome_line(reading, line) is True
    observation = reading_to_observation(reading, "live", "seeed_mr60bha2_esphome")
    assert observation["human_presence"] is True
    assert observation["breath_rate_bpm"] == 16
    assert observation["heart_rate_bpm"] == 74
    assert observation["distance_m"] == 0.9
    assert observation["num_targets"] == 1
    assert observation["illuminance_lx"] == 180
    assert observation["source_mode"] == "live"


def test_plain_demo_lines_fill_breath_heart_and_presence() -> None:
    reading = blank_reading()
    assert apply_plain_radar_line(reading, "total_phase: 0.00\tbreath_phase: 1.20\theart_phase: 0.40") is True
    assert apply_plain_radar_line(reading, "breath_rate: 15.50") is True
    assert apply_plain_radar_line(reading, "heart_rate: 72.00") is True
    assert apply_plain_radar_line(reading, "distance: 0.80") is True
    observation = reading_to_observation(reading, "live", "seeed_mr60bha2_text")
    assert observation["breath_rate_bpm"] == 15.5
    assert observation["heart_rate_bpm"] == 72.0
    assert observation["distance_m"] == 0.8
    assert observation["human_presence"] is True
    assert observation["breath_phase"] == 1.2


def test_plain_zero_rates_mean_no_one_is_locked() -> None:
    reading = blank_reading()
    assert apply_plain_radar_line(reading, "breath_rate: 0.00") is True
    assert apply_plain_radar_line(reading, "heart_rate: 0.00") is True
    observation = reading_to_observation(reading, "live", "seeed_mr60bha2_text")
    assert observation["human_presence"] is False
    assert observation["breath_rate_bpm"] == 0.0
    assert observation["heart_rate_bpm"] == 0.0


def test_binary_breath_frame_matches_the_module_layout() -> None:
    payload = struct.pack("<f", 16.0)
    frame = _frame(0x0A14, payload)
    found = parse_binary_frames(bytearray(b"\xff\x00" + frame))
    assert found == [{"breath_rate_bpm": 16.0}]


def test_dummy_sample_publishes_module_fields_without_a_bearing() -> None:
    _publish_dummy(1.0)
    radar = get_state().radar
    assert radar["source_mode"] == "simulation"
    assert radar["case_name"] == "dummy_mr60bha2"
    assert radar["human_presence"] is True
    assert radar["breath_rate_bpm"] is not None
    assert radar["heart_rate_bpm"] is not None
    assert radar["num_targets"] == 1
    assert radar["illuminance_lx"] is not None
    assert radar["display_bearing_deg"] is None
    assert radar["target_xy_m"] is None


def test_dummy_route_starts_and_stops() -> None:
    started = client.post("/api/radar/dummy")
    assert started.status_code == 200
    assert started.json()["ok"] is True
    stopped = client.post("/api/radar/stop")
    assert stopped.status_code == 200
    assert client.get("/api/operations/snapshot").json()["radar"] is None


def _frame(frame_type: int, payload: bytes) -> bytes:
    head = bytes([0x01, 0x00, 0x01, 0x00, len(payload), frame_type >> 8, frame_type & 0xFF])
    return head + bytes([_checksum(head)]) + payload + bytes([_checksum(payload)])
