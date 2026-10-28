import time

from app.config.geometry import search_lattice
from app.services import mic_window
from app.state import get_state


def test_the_stop_opens_the_mic_for_seven_seconds_then_closes_it(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(mic_window, "_start_mic", lambda: calls.append("on"))
    monkeypatch.setattr(mic_window, "_stop_mic_now", lambda: calls.append("off"))
    cell = search_lattice()[0]
    state = get_state()
    state.acoustic = {"class": "knock"}
    mic_window.begin_hold(cell, dwell_s=7.0, use_hardware=True)
    assert calls == ["on"]
    assert state.phase == "LISTEN"
    assert mic_window.publish_allowed() is True
    assert mic_window._timer is not None
    assert mic_window._timer.interval == 7.0
    mic_window.reset_window()
    assert mic_window.publish_allowed() is True


def test_after_the_stop_the_saved_sound_stays_and_new_samples_are_hidden(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(mic_window, "_start_mic", lambda: calls.append("on"))
    monkeypatch.setattr(mic_window, "_stop_mic_now", lambda: calls.append("off"))
    cell = search_lattice()[0]
    state = get_state()
    mic_window.begin_hold(cell, dwell_s=0.15, use_hardware=True)
    state.acoustic = {"class": "scratch/scrape"}
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and "off" not in calls:
        time.sleep(0.02)
    assert calls == ["on", "off"]
    assert mic_window.publish_allowed() is False
    assert state.phase == "SCANNING"
    assert state.heatmap[0]["readings"]["sound_category"] == "scrape"
    assert state.acoustic["class"] == "scratch/scrape"
    state.acoustic_waveform = [0.1]
    from app.audio.engine import _publish

    _publish({"class": "knock"}, [1.0], "knock", [0.9])
    assert state.acoustic["class"] == "scratch/scrape"
    assert state.acoustic_waveform == [0.1]
