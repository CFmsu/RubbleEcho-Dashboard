from app.ai.cost import estimate_usd
from app.ai.nebius_client import ai_status, interpret_model_text, interpret_scene, select_nvidia_model
from app.ai.prompts import build_messages
from app.services.mission import apply_model_result
from app.state import get_state


def test_status_hides_the_key(monkeypatch) -> None:
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key-not-real")
    monkeypatch.delenv("NEBIUS_MODEL_ID", raising=False)
    status = ai_status()
    assert status["status"] == "NOT_CONFIGURED"
    assert status["nvidia_online"] is False
    assert "test-key-not-real" not in str(status)


def test_catalog_selection_rejects_non_nvidia_models() -> None:
    assert select_nvidia_model(["meta-llama/Llama-3.1-8B"])["model_id"] is None
    chosen = select_nvidia_model(
        ["meta-llama/Llama-3.1-8B", "nvidia/nemotron-mini"],
        preferred="nvidia/nemotron-mini",
    )
    assert chosen["model_id"] == "nvidia/nemotron-mini"
    refused = select_nvidia_model(
        ["meta-llama/Llama-3.1-8B"],
        preferred="meta-llama/Llama-3.1-8B",
    )
    assert refused["reason"] == "preferred_model_is_not_nvidia"


def test_invalid_model_json_does_not_move() -> None:
    state = get_state()
    state.add_event(device="xvf3800", sensor="acoustic", summary="knock", quality="fixture")
    known = {state.events[0]["event_id"]}
    result, error = interpret_model_text(
        '{"recommendation":{"type":"move_cm","requires_approval":true,"point_id":null},"event_ids":["evt_0001"],"hypotheses":[{"label":"buried_impact_source","score":0.2,"evidence_event_ids":["evt_0001"],"limitations":["test"]}],"summary":"x","unknowns":[]}',
        known,
        {"A_FAR"},
        "nvidia/test",
        10,
        True,
    )
    assert result is None
    assert error == "recommendation_not_allowed"
    applied = apply_model_result({"ok": False, "kind": "invalid_json"})
    assert applied["nvidia_online"] is False
    assert get_state().safety == "STOP"
    assert get_state().solenoid.state == "DISARMED"
    assert get_state().command_log == []


def test_validator_rejects_auto_execute_and_unknown_ids() -> None:
    payload = {
        "event_ids": ["evt_0001"],
        "hypotheses": [
            {
                "label": "buried_impact_source",
                "score": 0.64,
                "evidence_event_ids": ["evt_0001"],
                "limitations": ["single surface measurement"],
            }
        ],
        "summary": "Impulse after a scheduled strike.",
        "recommendation": {
            "type": "rescan_at_point",
            "point_id": "A_FAR",
            "requires_approval": False,
        },
        "unknowns": ["radar through-sand validity"],
        "voltage": 12,
    }
    result, error = interpret_model_text(
        __import__("json").dumps(payload),
        {"evt_0001"},
        {"A_FAR"},
        "nvidia/test",
        12,
        False,
    )
    assert result is None
    assert error == "forbidden_key:voltage"
    payload.pop("voltage")
    result, error = interpret_model_text(
        __import__("json").dumps(payload),
        {"evt_0001"},
        {"A_FAR"},
        "nvidia/test",
        12,
        False,
    )
    assert result is None
    assert error == "approval_required"


def test_fenced_json_is_still_read() -> None:
    result, error = interpret_model_text(
        '```json\n{"event_ids":["evt_0001"],"hypotheses":[{"label":"check_A_NEAR","score":0.7,"evidence_event_ids":["evt_0001"],"limitations":["scripted sample"]}],"summary":"Check A_NEAR first. A knock was heard there.","recommendation":{"type":"rescan_at_point","point_id":"A_NEAR","requires_approval":true},"unknowns":["open air only"]}\n```',
        {"evt_0001"},
        {"A_NEAR"},
        "nvidia/test",
        12,
        False,
    )
    assert error is None
    assert result is not None
    assert result["recommendation"]["point_id"] == "A_NEAR"


def test_scene_note_rejects_a_motor_field() -> None:
    scene, error = interpret_scene(
        '{"scene":"Sand fills the frame.","obstacles":[],"open_area":"The middle is clear.","motor_speed":1}'
    )
    assert scene is None
    assert error == "forbidden_key:motor_speed"
    accepted, accepted_error = interpret_scene(
        '{"scene":"Sand fills the frame.","obstacles":["a dark block at the left"],"open_area":"The middle is clear."}'
    )
    assert accepted_error is None
    assert accepted is not None
    assert accepted["obstacles"] == ["a dark block at the left"]


def test_catalog_estimate_uses_the_published_nano_rate() -> None:
    assert estimate_usd("nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", 1_000_000, 0) == 0.06
    assert estimate_usd("nvidia/Nemotron-3.5-Super-VL", 0, 1_000_000) == 0.9
    assert estimate_usd("some-other-model", 100, 100) is None


def test_prompt_has_no_hidden_source() -> None:
    messages = build_messages(
        [{"event_id": "evt_0001", "summary": "knock", "value": 0.9, "unit": "raw"}],
        ["A_FAR", "B_NEAR"],
    )
    text = messages[1]["content"]
    assert "active_box" not in text
    assert "A_FAR" in text
