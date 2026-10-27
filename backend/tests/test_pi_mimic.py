from app.services.pi_mimic import publish_step
from app.state import get_state


def test_pi_mimic_uses_the_live_radar_line_shape() -> None:
    observation = publish_step(0)
    radar = get_state().radar
    assert radar["case_name"] == "Pi mimic"
    assert radar["source_mode"] == "simulation"
    assert observation["breath_rate_bpm"] == 16.0
    assert observation["heart_rate_bpm"] == 74.0
    assert observation["distance_m"] == 0.42
    assert observation["human_presence"] is True
    assert get_state().ultrasonic["distance_cm"] == 50.5
    assert get_state().ultrasonic["source_mode"] == "simulation"
    assert get_state().piezo_waveform


def test_quiet_pi_step_does_not_invent_a_person() -> None:
    observation = publish_step(3)
    assert observation["breath_rate_bpm"] == 0.0
    assert observation["heart_rate_bpm"] == 0.0
    assert observation["human_presence"] is False
