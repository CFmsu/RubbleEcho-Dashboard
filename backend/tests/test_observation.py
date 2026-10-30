from app.services.observation import (
    accept_result,
    attach_to_reasoning,
    build_observation,
    evidence_sufficiency,
    local_body,
    stamp_assessment,
    validate_assessment,
)


def _state(captures: list[dict], mode: str = "live") -> object:
    class State:
        cell_captures = captures
        trial_id = "trial-1"
        fixture_name = None
        pose = None

    state = State()
    state.mode = mode
    return state


def _cell(cell_id: str, ultrasonic: float | None, radar: float | None = None) -> dict:
    return {
        "point_id": cell_id,
        "readings": {
            "sound": None,
            "sound_category": None,
            "ultrasonic_cm": ultrasonic,
            "distance_m": radar,
            "audio_reason": None,
        },
        "evidence_event_ids": [],
    }


def test_a_stored_sound_is_a_microphone_reading() -> None:
    state = _state(
        [
            {
                "point_id": "r1c1",
                "readings": {"sound": "knock", "rms_dbfs": 0, "ultrasonic_cm": 40},
                "evidence_event_ids": [],
            }
        ]
    )
    observation = build_observation(state)
    assert observation["audio"] == {"sensor": "xvf3800", "status": "available"}
    assert observation["excluded"] == []
    assert any(row["sensor"] == "xvf3800" and row["value"] == "knock" for row in observation["readings"])
    assert observation["origin"] == "live"


def test_a_replay_snapshot_is_not_marked_live() -> None:
    state = _state([_cell("r1c1", 30)], mode="replay")
    assert build_observation(state)["origin"] == "replay"


def test_same_ranges_are_not_a_ranking() -> None:
    observation = build_observation(_state([_cell("r1c1", 40), _cell("r1c2", 40)]))
    report = evidence_sufficiency(observation)
    assert report["level"] == "limited"
    assert report["comparable"] is False


def test_different_ranges_can_name_a_cell() -> None:
    observation = build_observation(_state([_cell("r1c1", 40), _cell("r1c2", 12)]))
    report = evidence_sufficiency(observation)
    assert report["level"] == "supported"
    assert local_body(observation)["next_action"]["cell_id"] == "r1c2"


def test_malformed_and_invented_references_fail() -> None:
    observation = build_observation(_state([_cell("r1c1", 20)]))
    assert validate_assessment("not-json", observation)[1] == "invalid_json_shape"
    rejected, error = validate_assessment(
        {
            "summary": "Look at r9c9.",
            "findings": [{"text": "range", "evidence_id": "missing", "cell_id": "r1c1"}],
            "limitations": ["audio missing"],
            "next_action": {"type": "inspect_cell", "cell_id": "r1c1"},
        },
        observation,
    )
    assert rejected is None
    assert error == "unknown_evidence_id"


def test_a_survivor_claim_is_rejected() -> None:
    observation = build_observation(_state([_cell("r1c1", 20)]))
    _, error = validate_assessment(
        {
            "summary": "All clear. A survivor pulse was confirmed.",
            "findings": [],
            "limitations": ["none"],
            "next_action": {"type": "none", "cell_id": None},
        },
        observation,
    )
    assert error == "unsupported_claim"


def test_a_valid_model_body_keeps_server_identity() -> None:
    observation = build_observation(_state([_cell("r1c1", 20), _cell("r1c2", 50)]))
    body, error = validate_assessment(
        {
            "summary": "The closer ultrasonic reading is on row 1 column 1.",
            "findings": [
                {
                    "text": "Ultrasonic range 20 cm.",
                    "evidence_id": "r1c1:ultrasonic",
                    "cell_id": "r1c1",
                }
            ],
            "limitations": ["Audio was unavailable."],
            "next_action": {"type": "inspect_cell", "cell_id": "r1c1"},
        },
        observation,
    )
    assert error is None and body is not None
    stamped = stamp_assessment(
        body,
        observation,
        provider="nebius_token_factory",
        model_id="configured-model",
        latency_ms=12,
        live_call=True,
        request_id="req-new",
    )
    assert stamped["snapshot_id"] == observation["snapshot_id"]
    assert stamped["session_id"] == "trial-1"
    assert stamped["request_id"] == "req-new"
    assert stamped["live_call"] is True
    assert stamped["local_only"] is False
    assert stamped["next_action"]["type"] == "inspect_cell"
    assert "S" not in stamped["next_action"]["type"]


def test_a_stale_reply_cannot_replace_the_current_request() -> None:
    assert accept_result("trial-1", "req-old", "trial-1", "req-new") is False
    assert accept_result("trial-old", "req-new", "trial-1", "req-new") is False
    assert accept_result("trial-1", "req-new", "trial-1", "req-new") is True


def test_local_summary_is_not_labeled_as_a_cloud_result() -> None:
    state = _state([])
    result = {"summary": "No reliable impulse evidence is in the current trial.", "live_call": False}
    attach_to_reasoning(state, result)
    assert result["local_only"] is True
    assert result["evidence_sufficiency"] == "insufficient"
    assert state.observation["audio"]["status"] == "available"
    stamped = stamp_assessment(
        local_body(state.observation),
        state.observation,
        provider="local_deterministic",
        model_id=None,
        latency_ms=None,
        live_call=False,
        request_id="req-local",
    )
    assert stamped["local_only"] is True
    assert stamped["provider"] == "local_deterministic"
    assert "cloud" not in stamped["provider"]
