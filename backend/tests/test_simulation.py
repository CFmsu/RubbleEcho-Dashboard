from simulation import confidence_at


def test_legacy_confidence_still_orders_distance() -> None:
    assert confidence_at((5, 6), (6, 6), 0.0) > confidence_at((0, 0), (6, 6), 0.0)
