from app.control.state_machine import ScanMachine


def test_fault_stays_latched_until_acknowledged() -> None:
    machine = ScanMachine()
    assert machine.handle("start") == "CONNECT_CHECK"
    assert machine.handle("estop") == "FAULT_STOP"
    assert machine.handle("connected") == "FAULT_STOP"
    assert machine.acknowledge() == "IDLE"


def test_review_can_return_to_the_next_point() -> None:
    machine = ScanMachine()
    for event in (
        "start",
        "connected",
        "move",
        "arrived",
        "settled",
        "baseline_done",
        "window_done",
        "captured",
        "features_done",
        "classified",
        "fused",
        "reasoned",
        "approved_move",
    ):
        machine.handle(event)
    assert machine.stage == "MOVE_TO_TEST_POINT"
