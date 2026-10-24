import os

SYNC_TOLERANCE_MS = 50
ULTRASONIC_STOP_CM = 20
ULTRASONIC_CAUTION_CM = 40
MAX_MOVE_CM = 20.0
MAX_TURN_DEG = 45.0
POSE_TIMEOUT_MS = 1000
ENCODER_TIMEOUT_MS = 500
AI_MIN_INTERVAL_S = 5.0
AI_TIMEOUT_S = 20.0


def operator_token() -> str:
    return os.environ.get("OPERATOR_TOKEN", "")


def data_dir_override() -> str:
    return os.environ.get("RUBBLEECHO_DATA_DIR", "").strip()


def nebius_key() -> str:
    return os.environ.get("NEBIUS_API_KEY", "").strip()


def nebius_model() -> str:
    return os.environ.get("NEBIUS_MODEL_ID", "").strip()


def nebius_base_url() -> str:
    return os.environ.get(
        "NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"
    ).strip()


def probe_cameras() -> bool:
    return os.environ.get("RUBBLEECHO_PROBE_CAMERAS", "").strip() == "1"


def serial_port() -> str:
    return os.environ.get("RUBBLEECHO_SERIAL_PORT", "").strip()
