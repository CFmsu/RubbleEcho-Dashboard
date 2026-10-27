class SolenoidController:
    """Knock gate for the Arduino sketch on pin A0.

    One KNOCK is three taps: 200 ms high, 200 ms low. START repeats a group
    every 5 s. This object records the request. The serial write lives in
    solenoid_link and is the only path that asks the board to drive the pin.
    """

    PIN = "A0"
    PULSE_MS = 200
    GAP_MS = 200
    TAPS = 3
    INTERVAL_MS = 5000
    MAX_PULSE_MS = PULSE_MS
    ONSET_SEPARATION_MS = 250
    MAX_GROUP = TAPS

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.state = "DISARMED"
        self.fault: str | None = None
        self.pulses_in_group = 0
        self.last_onset_ms: int | None = None
        self.output_energized = False
        self.physically_confirmed = False
        self.log: list[dict] = []

    def arm(self, consent: bool) -> dict:
        self.output_energized = False
        if not consent:
            return self._result(False, "consent_required")
        if self.state == "FAULT":
            return self._result(False, "fault_latched")
        self.state = "ARMED"
        self.pulses_in_group = 0
        self.last_onset_ms = None
        self.fault = None
        return self._result(True, "armed_output_locked")

    def disarm(self) -> dict:
        self.state = "DISARMED"
        self.output_energized = False
        return self._result(True, "disarmed")

    def request_pulse(
        self,
        width_ms: int,
        rover_moving: bool,
        now_ms: int,
        consent: bool,
    ) -> dict:
        self.output_energized = False
        if self.state == "FAULT":
            return self._result(False, "fault_latched")
        if self.state == "COOLDOWN":
            return self._result(False, "cooldown")
        if not consent or self.state != "ARMED":
            return self._result(False, "disarmed")
        if rover_moving:
            self.state = "FAULT"
            self.fault = "rover_moving"
            return self._result(False, "rover_moving")
        if width_ms <= 0 or width_ms > self.MAX_PULSE_MS:
            self.state = "FAULT"
            self.fault = "pulse_width"
            return self._result(False, "pulse_width")
        if self.pulses_in_group >= self.MAX_GROUP:
            self.state = "COOLDOWN"
            return self._result(False, "cooldown")
        if (
            self.last_onset_ms is not None
            and now_ms - self.last_onset_ms < self.ONSET_SEPARATION_MS
        ):
            return self._result(False, "refractory")

        self.last_onset_ms = now_ms
        self.pulses_in_group += 1
        self.log.append(
            {
                "width_ms": width_ms,
                "now_ms": now_ms,
                "output_energized": False,
                "physically_confirmed": False,
            }
        )
        if self.pulses_in_group >= self.MAX_GROUP:
            self.state = "COOLDOWN"
        return self._result(True, "accepted_not_energized")

    def note_reference_sensor(self) -> dict:
        return {
            "physically_confirmed": False,
            "reason": "reference_piezo_not_in_inventory",
        }

    def public_status(self) -> dict:
        last = self.log[-1] if self.log else None
        return {
            "state": self.state,
            "output_energized": False,
            "physically_confirmed": False,
            "reference_sensor": "not_in_inventory",
            "fault": self.fault,
            "pulses_logged": len(self.log),
            "pulses_in_group": self.pulses_in_group,
            "last_request": last,
            "pattern": {
                "pin": self.PIN,
                "on_ms": self.PULSE_MS,
                "off_ms": self.GAP_MS,
                "taps": self.TAPS,
                "interval_ms": self.INTERVAL_MS,
            },
            "note": (
                "Arduino pin A0. One knock is three taps, 200 ms on and 200 ms off. "
                "START repeats that group every 5 s. STOP drives the pin low."
            ),
        }

    def _result(self, accepted: bool, reason: str) -> dict:
        return {
            "accepted": accepted,
            "reason": reason,
            "state": self.state,
            "output_energized": False,
            "physically_confirmed": False,
        }
