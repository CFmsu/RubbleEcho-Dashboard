from app.services.grid_route import first_step, note_scan, reset_route


def _beams(forward: float, left: float = 80, right: float = 80) -> list[dict]:
    return [
        {"deg": 0, "cm": left},
        {"deg": 45, "cm": left},
        {"deg": 90, "cm": forward},
        {"deg": 135, "cm": right},
        {"deg": 180, "cm": right},
    ]


def test_a_clear_sweep_keeps_the_snake() -> None:
    reset_route()
    assert note_scan("r1c1", 0, _beams(80)) == "r1c2"


def test_a_close_forward_reading_leaves_through_another_square() -> None:
    reset_route()
    assert note_scan("r1c1", 0, _beams(12)) == "r2c1"
    assert note_scan("r2c1", 90, _beams(80)) == "r2c2"
    assert note_scan("r2c2", 0, _beams(80)) == "r1c2"


def test_the_route_can_cross_a_visited_square_to_finish_the_grid() -> None:
    reset_route()
    note_scan("r1c1", 0, _beams(80))
    note_scan("r1c2", 0, _beams(80))
    assert note_scan("r1c3", 0, _beams(80, right=10)) == "r1c2"


def test_no_step_remains_after_every_square() -> None:
    reset_route()
    last = None
    for cell, heading in (
        ("r1c1", 0),
        ("r1c2", 0),
        ("r1c3", 0),
        ("r2c3", 90),
        ("r2c2", 180),
        ("r2c1", 180),
        ("r3c1", 90),
        ("r3c2", 0),
        ("r3c3", 0),
    ):
        last = note_scan(cell, heading, _beams(80))
    assert last is None


def test_first_step_skips_a_walled_off_square() -> None:
    blocked = {frozenset(("r1c1", "r1c2")), frozenset(("r2c2", "r1c2")), frozenset(("r1c3", "r1c2"))}
    assert first_step("r1c1", {"r1c1"}, blocked) == "r2c1"
