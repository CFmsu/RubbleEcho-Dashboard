from app.config.settings import serial_port
from app.services.feature_extraction import classify_window


def device_report() -> dict:
    """USB capture is not opened in this process unless a later hardware build does so."""
    return {
        "device_id": "xvf3800",
        "state": "disconnected",
        "source_mode": "unavailable",
        "channels": None,
        "sample_rate_hz": None,
        "firmware_mode": "not_enumerated",
        "error": "USB audio device has not been opened. Channel count is unknown.",
        "status": "NEEDS_HARDWARE_VERIFICATION",
    }


def classify_captured_window(
    samples: list[float],
    sample_rate: float,
    captured_at_utc: str | None = None,
    context: dict | None = None,
) -> dict:
    return classify_window(samples, sample_rate, captured_at_utc, context)


def configured_serial_port() -> str:
    # The microphone array is USB. This helper exists so callers do not reuse the
    # radar serial port as a stand-in for the XVF3800.
    return serial_port()
