"""Scan stages. A fault stays latched until a person acknowledges it."""

TRANSITIONS = {
    ("IDLE", "start"): "CONNECT_CHECK",
    ("CONNECT_CHECK", "connected"): "READY",
    ("READY", "move"): "MOVE_TO_TEST_POINT",
    ("MOVE_TO_TEST_POINT", "arrived"): "STOP_AND_SETTLE",
    ("STOP_AND_SETTLE", "settled"): "BASELINE",
    ("BASELINE", "baseline_done"): "ACTIVE_SIGNAL_WINDOW",
    ("ACTIVE_SIGNAL_WINDOW", "window_done"): "CAPTURE",
    ("CAPTURE", "captured"): "EXTRACT_FEATURES",
    ("EXTRACT_FEATURES", "features_done"): "CLASSIFY",
    ("CLASSIFY", "classified"): "FUSE",
    ("FUSE", "fused"): "REASON",
    ("REASON", "reasoned"): "REVIEW_ACTION",
    ("REVIEW_ACTION", "approved_move"): "MOVE_TO_TEST_POINT",
    ("REVIEW_ACTION", "complete"): "COMPLETE",
}

FAULT_EVENTS = {"estop", "fault", "stale_command", "lost_serial", "invalid_position"}


class ScanMachine:
    def __init__(self) -> None:
        self.stage = "IDLE"

    def handle(self, event: str) -> str:
        if self.stage == "FAULT_STOP":
            return self.stage
        if event in FAULT_EVENTS:
            self.stage = "FAULT_STOP"
            return self.stage
        nxt = TRANSITIONS.get((self.stage, event))
        if nxt is None:
            return self.stage
        self.stage = nxt
        return self.stage

    def acknowledge(self) -> str:
        if self.stage != "FAULT_STOP":
            return self.stage
        self.stage = "IDLE"
        return self.stage
