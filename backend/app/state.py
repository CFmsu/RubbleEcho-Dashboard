from app.drivers.camera_pi import default_cameras
from app.drivers.solenoid import SolenoidController
from app.vision.aruco import aruco_backend_status

DEVICE_CATALOG = [
    ("raspberry_pi_4", "edge_computer", "disconnected", "This process has not enumerated the Pi."),
    ("camera_top", "camera", "disconnected", "Camera not opened."),
    ("camera_ground_coordinate", "camera", "disconnected", "Camera not opened."),
    ("camera_ground_inspection", "camera", "disconnected", "Camera not opened."),
    ("arduino_uno", "motor_controller", "disconnected", "No verified motor link."),
    ("arduino_mega", "sensor_controller", "unsupported", "Board model is not verified."),
    ("esp32", "sensor_bridge", "disconnected", "Serial port is not configured."),
    ("mr60bha2", "radar", "disconnected", "No live radar frames."),
    ("hc_sr04", "ultrasonic", "disconnected", "No live obstacle samples."),
    ("xvf3800", "microphone_array", "disconnected", "USB audio device is not opened."),
    ("piezo", "contact_vibration", "disconnected", "No ADC samples. Assigned role: stationary surface contact receiver."),
    ("solenoid", "knock_source", "disconnected", "Output locked. Default disarmed."),
    ("bluetooth", "optional_manual_link", "unsupported", "Module type is not verified. Not an autonomy link."),
    ("nebius_nvidia", "advisory_model", "disconnected", "No verified live NVIDIA call."),
]

LIMITATIONS = [
    "Prototype only. Not a certified search-and-rescue or medical device.",
    "Radar through-sand vital signs are not validated.",
    "Heatmap values are uncalibrated heuristic scores at measured points.",
    "The sand-table coordinates are plan inferences pending a physical survey.",
    "The single piezo is assigned as a surface contact receiver. A buried reference piezo is not in the inventory.",
]


def blank_device(device_id: str, device_type: str, state: str, error: str) -> dict:
    return {
        "device_id": device_id,
        "device_type": device_type,
        "source_mode": "unavailable",
        "state": state,
        "last_seen_utc": None,
        "age_ms": None,
        "sampling_rate_hz": None,
        "firmware": None,
        "driver": None,
        "quality": "not_enumerated",
        "error": error,
    }


class AppState:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.mode = "unavailable"
        self.phase = "IDLE"
        self.safety = "HOLD"
        self.legacy_active = False
        self.operator_link = False
        self.trial_id: str | None = None
        self.trial: dict | None = None
        self.devices = [
            blank_device(device_id, device_type, state, error)
            for device_id, device_type, state, error in DEVICE_CATALOG
        ]
        self.cameras = default_cameras()
        self.radar = None
        self.ultrasonic = None
        self.acoustic = None
        self.impulse = None
        self.piezo = None
        self.pose = None
        self.pose_trail: list[dict] = []
        self.solenoid = SolenoidController()
        self.events: list[dict] = []
        self.samples: list[dict] = []
        self.heatmap: list[dict] = []
        self.reasoning = None
        self.seen_command_ids: set[str] = set()
        self.command_log: list[dict] = []
        self.sequence = 0
        self.fixture_name = None
        self.malformed_radar = 0
        self.acoustic_envelope: list[float] = []
        self.impulse_envelope: list[float] = []
        self.calibration = {
            "marker_count": 0,
            "homography_valid": False,
            "pose_valid": False,
            "rms_px": None,
            "reason": "no_calibration",
            "pose_quality": "unavailable",
            "aruco": aruco_backend_status(),
        }
        self.last_ai_monotonic = 0.0

    def add_event(self, **fields: object) -> dict:
        self.sequence += 1
        event = {
            "event_id": f"evt_{self.sequence:04d}",
            "mode": self.mode,
            **fields,
        }
        self.events.append(event)
        self.events = self.events[-200:]
        return event

    def mark_replay_device(self, device_id: str, seen_utc: str) -> None:
        for device in self.devices:
            if device["device_id"] != device_id:
                continue
            device["state"] = "connected"
            device["source_mode"] = "replay"
            device["quality"] = "replay_fixture"
            device["last_seen_utc"] = seen_utc
            device["age_ms"] = 0
            device["driver"] = "fixture"
            device["error"] = None


_STATE: AppState | None = None


def get_state() -> AppState:
    global _STATE
    if _STATE is None:
        _STATE = AppState()
    return _STATE
