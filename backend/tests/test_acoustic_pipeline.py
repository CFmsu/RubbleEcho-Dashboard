import numpy as np
from fastapi.testclient import TestClient

from app.audio.detector import AcousticCalibration
from app.audio.dummy_dataset import accepts, build_clip
from app.audio.engine import run_mics
from app.drivers.respeaker import deinterleave_mics, device_report
from app.services.feature_extraction import StreamingBandpass
from app.services.fusion import gcc_phat_delays
from main import app

client = TestClient(app)


def test_block_filter_matches_a_single_pass() -> None:
    rng = np.random.default_rng(3)
    samples = rng.normal(0.0, 0.05, size=(2400, 4))
    whole = StreamingBandpass().process(samples)
    split = StreamingBandpass()
    parts = [split.process(samples[:800]), split.process(samples[800:1600]), split.process(samples[1600:])]
    assert np.allclose(np.vstack(parts), whole, atol=1e-9)


def test_deinterleave_keeps_four_mics_and_drops_the_mix() -> None:
    frames = np.arange(12, dtype=np.int16).reshape(2, 6)
    mics = deinterleave_mics(frames, (0, 1, 2, 3))
    assert mics.shape == (2, 4)
    assert np.allclose(mics[0], np.arange(4) / 32768.0)


def test_dummy_knock_scratch_and_rejects() -> None:
    calibration = AcousticCalibration()
    for kind in ("silence", "knock", "scratch", "whine", "rumble", "scratch_short", "scratch_long", "periodic"):
        events = run_mics(build_clip(kind, np.random.default_rng(11)), calibration)
        labels = {event["class"] for event in events}
        assert accepts(kind, labels), (kind, labels)
        if kind == "knock":
            delays = events[0]["tdoa"]["delays_samples"]
            assert events[0]["tdoa"]["valid"] is True
            for channel, expected in enumerate((0, 1, -1, 2)):
                assert abs(delays[channel] - expected) < 0.45


def test_gcc_phat_recovers_a_one_sample_delay() -> None:
    rng = np.random.default_rng(5)
    base = rng.normal(0.0, 1.0, size=512)
    mics = np.zeros((512, 4))
    delays = (0, 1, -1, 2)
    for channel, delay in enumerate(delays):
        shifted = np.roll(base, delay)
        if delay > 0:
            shifted[:delay] = 0
        elif delay < 0:
            shifted[delay:] = 0
        mics[:, channel] = shifted
    result = gcc_phat_delays(mics, sample_rate=16000, max_lag=3)
    assert result["valid"] is True
    for channel, delay in enumerate(delays):
        assert abs(result["delays_samples"][channel] - delay) < 0.45


def test_device_report_does_not_open_a_missing_array() -> None:
    report = device_report()
    assert report["device_id"] == "xvf3800"
    assert report["piezo"] is False
    assert report["state"] in {"disconnected", "ready"}
    if report["state"] != "ready":
        assert report["sample_rate_hz"] is None


def test_listen_route_refuses_a_missing_array() -> None:
    response = client.post("/api/audio/listen")
    if response.status_code == 200:
        assert client.post("/api/audio/stop").status_code == 200
        return
    assert response.status_code == 409
    assert response.json()["detail"]["ok"] is False
