from app.services.feature_extraction import classify_window
from app.services.sensor_feed import apply_line
from app.services.signals import place_echo
from app.services.sim_media import sample_wav
from app.services.sim_run import start_run
from app.state import get_state


def test_scripted_clips_keep_their_classes_and_are_not_flat() -> None:
    for kind, label in (("knock", "knock"), ("scratch", "scratch/scrape"), ("ambient", "ambient")):
        _wav, samples = sample_wav(kind)
        heard = classify_window(samples[:1600], 16000)
        assert heard["class"] == label
        assert max(samples[:1600]) != min(samples[:1600])


def test_echo_point_moves_when_distance_changes() -> None:
    state = get_state()
    state.pose = {"x_cm": 40.0, "y_cm": 30.0, "heading_deg": 0.0, "valid": True}
    state.ultrasonic = {"distance_cm": 12.0, "echo_timeout": False}
    place_echo(state)
    near = state.ultrasonic["echo_x_cm"]
    state.ultrasonic["distance_cm"] = 48.0
    place_echo(state)
    far = state.ultrasonic["echo_x_cm"]
    assert far > near
    assert state.ultrasonic["echo_y_cm"] == 30.0


def test_live_lines_fill_the_same_fields_and_a_close_return_reroutes() -> None:
    start_run(schedule=False)
    state = get_state()
    state.scan_route = [
        {"id": "x12y12", "x_cm": 12.0, "y_cm": 12.0},
        {"id": "x22y12", "x_cm": 22.0, "y_cm": 12.0},
        {"id": "A_NEAR", "x_cm": 32.0, "y_cm": 12.0},
    ]
    state.pose = {"x_cm": 12.0, "y_cm": 12.0, "heading_deg": 0.0, "valid": True, "source": "test"}
    apply_line('ULTRASONIC {"distance_cm": 14.2, "echo_timeout": false}')
    assert state.ultrasonic["source_mode"] == "live"
    assert state.ultrasonic["distance_cm"] == 14.2
    assert state.scan_route[0]["blocked"] is True
    assert "x12y12" in state.blocked_cells
    assert state.phase == "LISTEN"
    assert state.ultrasonic["echo_x_cm"] is not None
    apply_line('PIEZO {"samples": [4, 120, -80, 10, -6], "sample_rate_hz": 1000}')
    assert state.piezo["source_mode"] == "live"
    assert state.piezo["peak_adc_counts"] == 120
    assert len(state.piezo_waveform) >= 4
    apply_line('ENC {"left_delta": 3, "right_delta": 8}')
    apply_line('ENC {"left_delta": 4, "right_delta": 1}')
    assert state.rover_trace["left"] == [3.0, 4.0]
    assert state.rover_trace["right"] == [8.0, 1.0]
    assert state.rover_trace["source_mode"] == "live"
    assert any(device["device_id"] == "hc_sr04" and device["source_mode"] == "live" for device in state.devices)
