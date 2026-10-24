import json
import math

from app.audio.cli import main
from app.audio.detector import detect_event


def test_silence_and_impulse_stay_finite_and_untrained() -> None:
    silence = detect_event([0.0] * 32, 16000)
    impulse = [0.0] * 32
    impulse[4] = 0.9
    knock = detect_event(impulse, 16000)
    empty = detect_event([], 16000)
    assert silence["event"] == "BACKGROUND"
    assert knock["event"] == "POSSIBLE_KNOCK"
    assert empty["event"] == "UNKNOWN"
    for result in (silence, knock, empty):
        assert result["training_status"] == "NOT_TRAINED"
        assert result["score"] is None
        assert result["heartbeat"] == "UNVERIFIED"
        assert result["finite"] is True
        for value in result["features"].values():
            if value is not None:
                assert math.isfinite(value)


def test_train_command_does_not_claim_a_model(capsys) -> None:
    assert main(["train"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["training_status"] == "NOT_TRAINED"


def test_record_command_does_not_invent_audio() -> None:
    assert main(["record"]) == 2
