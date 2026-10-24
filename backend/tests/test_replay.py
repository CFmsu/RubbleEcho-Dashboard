import json

from fastapi.testclient import TestClient

from app.drivers.radar_mr60bha2 import parse_radar_line
from app.drivers.serial_bridge import backoff_sequence, handle_line
from app.services.feature_extraction import classify_window
from main import app

client = TestClient(app)


def test_radar_parser_cases() -> None:
    stale, error = parse_radar_line(
        '{"human_presence":true,"breath_rate_bpm":12,"stability":"stationary","stale":true,"valid":true}'
    )
    assert error is None
    assert stale is not None
    assert stale["stale"] is True
    assert stale["breath_rate_bpm"] is None
    assert stale["target_xy_m"] is None

    moving, _ = parse_radar_line(
        '{"human_presence":true,"breath_rate_bpm":14,"heart_rate_bpm":70,"stability":"moving","breath_retained":true}'
    )
    assert moving is not None
    assert moving["breath_rate_bpm"] is None
    assert moving["heart_rate_bpm"] is None
    assert "breath_retained_value_suppressed" in moving["notes"]

    ignored, ignored_error = parse_radar_line(
        '{"human_presence":true,"micro_displacement_mm":0.42,"stability":"stationary"}'
    )
    assert ignored is None
    assert ignored_error is not None
    assert "micro_displacement_mm" in ignored_error

    spatial, _ = parse_radar_line(
        '{"human_presence":true,"stability":"stationary","target_xy_m":[0.2,0.1],"spatial_coordinates_supported":true,"valid":true}'
    )
    assert spatial is not None
    assert spatial["target_xy_m"] == [0.2, 0.1]

    unverified_xy, _ = parse_radar_line(
        '{"human_presence":false,"stability":"stationary","target_xy_m":[1,2],"valid":true}'
    )
    assert unverified_xy is not None
    assert unverified_xy["target_xy_m"] is None
    assert "xy_ignored_firmware_unverified" in unverified_xy["notes"]


def test_status_line_is_not_a_detection() -> None:
    handled = handle_line('{"device":"esp32","status":"NEEDS_HARDWARE_VERIFICATION"}')
    assert handled["kind"] == "ignored"
    assert handled["observation"] is None
    assert backoff_sequence(3) == [0.5, 1.0, 2.0]


def test_audio_classes_do_not_invent_speech_or_a_person() -> None:
    silence = classify_window([0.0] * 32, 16000)
    knock = classify_window([0.0] * 16 + [0.95, -0.8, 0.2] + [0.0] * 13, 16000)
    scratch = classify_window([0.22] * 32, 16000)
    tone = [0.08] * 32
    sustained = classify_window(tone, 16000)
    assert silence["class"] == "silence"
    assert knock["class"] == "knock"
    assert knock["origin_unknown"] is True
    assert scratch["class"] == "scratch/scrape"
    assert sustained["class"] in {"unknown", "ambient"}
    assert sustained["class"] != "speech"
    assert "survivor" not in json.dumps(knock)


def test_replay_snapshot_is_labeled_and_hides_ground_truth(auth_header) -> None:
    started = client.post(
        "/api/trials/start",
        json={"mode": "replay", "fixture": "sample_trial"},
        headers=auth_header,
    )
    assert started.status_code == 200
    current = client.get("/api/operations/snapshot").json()
    assert current["badge"] == "REPLAY"
    assert current["mode"] == "replay"
    assert current["system_live"] is False
    assert current["nvidia_online"] is False
    assert current["streaming_camera_count"] == 0
    assert current["radar"]["human_presence"] is False
    assert current["radar"]["target_xy_m"] is None
    assert current["radar"]["breath_rate_bpm"] is None
    assert current["ultrasonic"]["distance_cm"] == 55
    assert current["solenoid"]["output_energized"] is False
    assert current["solenoid"]["state"] == "DISARMED"
    encoded = json.dumps(current)
    assert "active_box" not in encoded
    assert "actual_source" not in encoded
    assert "evaluator_only" not in encoded
    scores = {point["point_id"]: point for point in current["heatmap_points"]}
    assert scores["A_FAR"]["interpolated"] is False
    assert scores["A_FAR"]["score"] > scores["B_NEAR"]["score"]
    devices = {item["device_id"]: item for item in current["devices"]}
    assert devices["mr60bha2"]["source_mode"] == "replay"
    assert devices["camera_top"]["state"] == "disconnected"
    assert devices["nebius_nvidia"]["state"] == "disconnected"
    assert all(point["source_mode"] != "live" for point in current["heatmap_points"])
