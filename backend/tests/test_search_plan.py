from app.services.search_plan import _accept_model_plan, _local_plan, apply_obstacle, apply_signal, plan_from_photo
from app.state import get_state


def test_plan_covers_every_grid_cell_without_a_motor_command() -> None:
    body = plan_from_photo()
    plan = body["plan"]
    assert body["ok"] is True
    assert plan["execute_hardware"] is False
    assert plan["ultrasonic"]["commanded_pin"] is None
    assert set(plan["path"]) == {"A_NEAR", "A_FAR", "B_NEAR", "B_FAR", "C_NEAR", "C_FAR"}
    assert len(plan["boundary"]) == 4
    assert "model is not configured" in body["message"]


def test_close_obstacle_blocks_a_cell_and_rotates_the_planned_look() -> None:
    plan_from_photo()
    state = get_state()
    state.ultrasonic = {
        "distance_cm": 12,
        "echo_timeout": False,
        "direction": "forward",
        "quality": "test",
        "notes": [],
        "source_mode": "simulation",
    }
    body = apply_obstacle()
    assert body["ok"] is True
    blocked = [cell["point_id"] for cell in body["plan"]["cells"] if cell["state"] == "blocked"]
    assert blocked == [body["plan"]["obstacle"]["blocked_point_id"]]
    assert body["plan"]["look"] == "left"
    assert blocked[0] not in body["plan"]["path"]


def test_missing_echo_does_not_invent_a_block() -> None:
    plan_from_photo()
    body = apply_obstacle()
    assert body["ok"] is False
    assert get_state().search_plan["path"]


def test_radar_presence_paints_the_heatmap_on_the_current_cell() -> None:
    plan_from_photo()
    state = get_state()
    state.radar = {"human_presence": True, "source_mode": "simulation", "distance_m": 0.8}
    first = state.search_plan["path"][0]
    body = apply_signal()
    assert body["ok"] is True
    assert body["heatmap_point"]["point_id"] == first
    assert body["heatmap_point"]["method"] == "signal_at_grid_cell"
    assert state.heatmap[-1]["point_id"] == first
    assert state.reasoning is not None
    assert first not in state.search_plan["path"]


def test_model_boundary_outside_the_table_keeps_the_inset() -> None:
    local = _local_plan({"frame": "not_stored", "note": "test"})
    text = '{"boundary":[{"x1_cm":-5,"y1_cm":0,"x2_cm":10,"y2_cm":0}],"path":["A_NEAR","A_FAR"],"look":"Right"}'
    plan, reason = _accept_model_plan(text, local)
    assert reason == ""
    assert plan is not None
    assert plan["path"] == ["A_NEAR", "A_FAR"]
    assert plan["look"] == "right"
    assert plan["boundary"] == local["boundary"]
    assert plan["boundary_replaced"] is True


def test_model_plan_with_a_motor_field_is_rejected() -> None:
    local = _local_plan({"frame": "not_stored", "note": "test"})
    text = '{"boundary":[{"x1_cm":12,"y1_cm":12,"x2_cm":90,"y2_cm":12}],"path":["A_NEAR"],"look":"left","motor_speed":40}'
    assert _accept_model_plan(text, local)[0] is None
