from app.config.geometry import search_lattice
from app.services.rover_track import apply_rover_line
from app.services.sim_run import _pose
from app.state import get_state


def test_reported_cell_is_the_measured_center() -> None:
    state = get_state()
    state.reset()
    route = search_lattice()
    state.scan_route = route
    assert apply_rover_line('ACK {"device":"arduino_uno","cell":"r1c2","phase":"hold"}')
    from app.services.grid_route import sweep_status

    assert sweep_status()["ready"] is True
    assert sweep_status()["cell"] == "r1c2"
    cell = next(item for item in route if item["id"] == "r1c2")
    assert state.pose["source"] == "arduino_uno"
    assert state.pose["cell_id"] == "r1c2"
    assert state.pose["x_cm"] == cell["x_cm"]
    assert state.pose["y_cm"] == cell["y_cm"]
    assert state.rover_leg is None
    assert state.pose_trail[-1]["cell_id"] == "r1c2"


def test_moving_report_draws_the_leg_between_cells() -> None:
    state = get_state()
    state.reset()
    route = search_lattice()
    state.scan_route = route
    assert apply_rover_line(
        'ACK {"device":"arduino_uno","status":"moving","from":"r1c3","to":"r2c3","ms":1800}'
    )
    origin = next(item for item in route if item["id"] == "r1c3")
    dest = next(item for item in route if item["id"] == "r2c3")
    assert state.rover_leg["from_x_cm"] == origin["x_cm"]
    assert state.rover_leg["to_y_cm"] == dest["y_cm"]
    assert state.rover_leg["duration_ms"] == 1800


def test_reported_site_uses_the_surveyed_coordinate() -> None:
    state = get_state()
    state.reset()
    assert apply_rover_line('ACK {"device":"arduino_uno","cell":"A_NEAR","phase":"hold"}')
    assert state.pose["cell_id"] == "A_NEAR"
    assert state.pose["x_cm"] == 52.5
    assert state.pose["y_cm"] == 14.5
    assert apply_rover_line(
        'ACK {"device":"arduino_uno","status":"moving","from":"A_NEAR","to":"A_FAR","cm":25.0,"ms":1125}'
    )
    assert state.rover_leg["distance_cm"] == 25.0
    assert state.rover_leg["to_x_cm"] == 52.5
    assert state.rover_leg["to_y_cm"] == 39.5


def test_each_square_is_its_own_listen_and_the_briefing_names_the_row() -> None:
    state = get_state()
    state.reset()
    assert apply_rover_line('ACK {"device":"arduino_uno","status":"grid_started"}')
    assert apply_rover_line('ACK {"device":"arduino_uno","cell":"r1c1","phase":"hold"}')
    assert state.heatmap == []
    assert state.cell_captures[0]["point_id"] == "r1c1"
    assert state.cell_captures[0]["readings"]["place"] == "row 1, the first square"
    assert apply_rover_line('ACK {"device":"arduino_uno","cell":"r2c3","phase":"hold"}')
    assert [point["point_id"] for point in state.cell_captures] == ["r1c1", "r2c3"]
    assert apply_rover_line('ACK {"device":"arduino_uno","status":"grid_done"}')
    assert [point["point_id"] for point in state.heatmap] == ["r1c1", "r2c3"]
    assert "row 1, the first square" in state.reasoning["narrative"]


def test_a_moving_rover_does_not_keep_the_microphone_trace() -> None:
    state = get_state()
    state.reset()
    state.scan_route = search_lattice()
    state.acoustic = {"class": "knock"}
    state.acoustic_waveform = [0.4, 0.2]
    assert apply_rover_line(
        'ACK {"device":"arduino_uno","status":"moving","from":"r1c1","to":"r1c2","ms":1500}'
    )
    assert state.acoustic is None
    assert state.acoustic_waveform == []
    assert state.phase == "SCANNING"


def test_a_pi_sweep_reroutes_while_the_rover_is_stopped() -> None:
    from app.services import grid_route
    from app.services.rover_track import apply_pi_sweep

    state = get_state()
    state.reset()
    assert apply_rover_line(
        'ACK {"device":"arduino_uno","status":"arrived","cell":"r1c1","heading":0}'
    )
    assert grid_route.sweep_status()["ready"] is True
    result = apply_pi_sweep(
        [{"deg": 0, "cm": 90}, {"deg": 90, "cm": 11}, {"deg": 180, "cm": 90}]
    )
    assert result["next"] == "r2c1"
    assert state.ultrasonic["distance_cm"] == 11
    assert "r2c1" in state.events[-1]["summary"]


def test_scripted_pose_leaves_a_live_fix_in_place() -> None:
    state = get_state()
    state.reset()
    state.motor_tracking = True
    state.pose = {"source": "arduino_uno", "x_cm": 18.8, "cell_id": "r1c1"}
    _pose(state, {"x_cm": 86.2, "y_cm": 65.3}, "2026-01-01T00:00:00Z", 180.0)
    assert state.pose["cell_id"] == "r1c1"
