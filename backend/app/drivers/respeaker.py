"""XVF3800 raw capture.

The host must already be running the 6-channel developer firmware
(4 microphones, 1 AEC loopback, 1 processed mix), flashed with the XMOS DFU
tool before this process starts. This module does not flash firmware and it
does not turn AGC or noise suppression off. Those blocks stay inside the chip
until that image is installed.

Open the hardware device, not a plug plugin:
  Linux: the ALSA name from `arecord -l`, passed as RUBBLEECHO_AUDIO_DEVICE.
         Example shape: hw:CARD=XVF3800,DEV=0. Do not use plughw. plughw resamples.
  Windows: sounddevice's host-API name. There is no ALSA string here.
         The Listen button uses whichever input enumerates as XVF3800 / ReSpeaker
         with at least 6 channels.

Stream contract: 6 channels, 16000 Hz, int16. Frames arrive interleaved.
Columns in the default map are mics 0,1,2,3. Columns 4 and 5 (loopback and
processed voice) are discarded. Confirm the four mic indexes with a one-capsule
tap and set RUBBLEECHO_MIC_INDEXES if the image orders them differently.
The loopback channel is speaker reference, not a piezo.
"""

from __future__ import annotations

import os
import threading

from app.config.settings import serial_port
from app.services.feature_extraction import classify_window

RATE_HZ = 16000
RAW_CHANNELS = 6
BLOCK_SAMPLES = 512
_NAME_NEEDLES = ("xvf3800", "respeaker", "seeed")


def device_report() -> dict:
    """Query the host audio API. Does not leave a stream open."""
    try:
        import sounddevice as sd
    except ImportError:
        return _report(
            "disconnected",
            "not_enumerated",
            None,
            "sounddevice is not installed. Install backend/requirements-hardware.txt before plugging in the XVF3800.",
        )
    try:
        found = _match_input(sd)
    except Exception as exc:
        return _report("disconnected", "not_enumerated", None, f"Audio host query failed: {exc}")
    if found is None:
        return _report(
            "disconnected",
            "not_enumerated",
            None,
            "XVF3800 was not enumerated. Plug in the array. On the Pi, confirm the card with arecord -l.",
        )
    channels = int(found["max_input_channels"])
    if channels < RAW_CHANNELS:
        return _report(
            "disconnected",
            "processed_voice_stream" if channels <= 2 else "unexpected_channel_count",
            channels,
            (
                f"{found['name']} exposes {channels} input channel(s), not 6. "
                "That is the processed voice stream. Flash the 6-channel raw image with the XMOS DFU tool, replug, "
                "and open the hw: device (Linux) or the 6-channel host endpoint (Windows)."
            ),
            device_index=found["index"],
            device_name=found["name"],
        )
    return _report(
        "ready",
        "raw_6ch_assumed",
        channels,
        None,
        device_index=found["index"],
        device_name=found["name"],
    )


def classify_captured_window(
    samples: list[float],
    sample_rate: float,
    captured_at_utc: str | None = None,
    context: dict | None = None,
) -> dict:
    """Offline mono fixture path. Live audio goes through iter_mic_blocks instead."""
    return classify_window(samples, sample_rate, captured_at_utc, context)


def configured_serial_port() -> str:
    # The microphone array is USB. This helper exists so callers do not reuse the
    # radar serial port as a stand-in for the XVF3800.
    return serial_port()


def iter_mic_blocks(stop: threading.Event):
    """Yield float blocks shaped (frames, 4), one column per raw mic."""
    import sounddevice as sd

    report = device_report()
    if report["state"] != "ready":
        raise RuntimeError(report["error"] or "XVF3800 is not ready")
    queue = _queue()
    indexes = mic_indexes()

    def callback(indata, frames, time_info, status) -> None:
        del frames, time_info
        if stop.is_set():
            raise sd.CallbackStop()
        if status and status.input_overflow:
            queue.put(("overflow", None))
            return
        queue.put(("audio", indata.copy()))

    with sd.InputStream(
        device=_device_arg(report),
        channels=RAW_CHANNELS,
        samplerate=RATE_HZ,
        dtype="int16",
        blocksize=BLOCK_SAMPLES,
        callback=callback,
    ):
        while not stop.is_set():
            try:
                kind, payload = queue.get(timeout=0.2)
            except Exception:
                continue
            if kind == "overflow":
                continue
            yield deinterleave_mics(payload, indexes)


def deinterleave_mics(block, indexes: tuple[int, int, int, int] | None = None):
    """Slice an interleaved (frames, 6) int16 buffer down to four float mics in [-1, 1]."""
    import numpy as np

    data = np.asarray(block)
    if data.ndim != 2:
        raise ValueError("expected an interleaved frame buffer shaped (frames, channels)")
    chosen = indexes or mic_indexes()
    if data.shape[1] <= max(chosen):
        raise ValueError(
            f"stream has {data.shape[1]} channels; mic indexes {chosen} do not fit. "
            "Refusing to treat a processed mix as raw mics."
        )
    mics = data[:, list(chosen)]
    if np.issubdtype(mics.dtype, np.integer):
        return mics.astype(np.float64) / 32768.0
    return mics.astype(np.float64)


def mic_indexes() -> tuple[int, int, int, int]:
    raw = os.environ.get("RUBBLEECHO_MIC_INDEXES", "0,1,2,3")
    parts = [int(piece) for piece in raw.split(",") if piece.strip()]
    if len(parts) != 4 or any(part < 0 or part > 5 for part in parts) or len(set(parts)) != 4:
        return (0, 1, 2, 3)
    return (parts[0], parts[1], parts[2], parts[3])


def _match_input(sd) -> dict | None:
    override = os.environ.get("RUBBLEECHO_AUDIO_DEVICE", "").strip()
    devices = sd.query_devices()
    candidates = []
    for index, item in enumerate(devices):
        if int(item["max_input_channels"]) < 1:
            continue
        name = str(item["name"])
        candidates.append({"index": index, "name": name, "max_input_channels": int(item["max_input_channels"])})
    if override:
        if override.isdigit():
            index = int(override)
            return next((item for item in candidates if item["index"] == index), None)
        narrowed = [item for item in candidates if override.lower() in item["name"].lower()]
        return max(narrowed, key=lambda item: item["max_input_channels"], default=None)
    named = [item for item in candidates if any(needle in item["name"].lower() for needle in _NAME_NEEDLES)]
    if not named:
        return None
    return max(named, key=lambda item: item["max_input_channels"])


def _device_arg(report: dict):
    override = os.environ.get("RUBBLEECHO_AUDIO_DEVICE", "").strip()
    if override and not override.isdigit():
        return override
    return report.get("device_index")


def _report(
    state: str,
    firmware_mode: str,
    channels: int | None,
    error: str | None,
    device_index: int | None = None,
    device_name: str | None = None,
) -> dict:
    mics = list(mic_indexes()) if channels and channels >= RAW_CHANNELS else None
    discarded = [index for index in range(RAW_CHANNELS) if mics is not None and index not in mics]
    return {
        "device_id": "xvf3800",
        "state": state,
        "source_mode": "unavailable",
        "channels": channels,
        "sample_rate_hz": RATE_HZ if state == "ready" else None,
        "sample_format": "int16" if state == "ready" else None,
        "firmware_mode": firmware_mode,
        "device_index": device_index,
        "device_name": device_name,
        "mic_indexes": mics,
        "discarded_indexes": discarded or None,
        "error": error,
        "status": "READY" if state == "ready" else "NEEDS_HARDWARE_VERIFICATION",
        "piezo": False,
    }


def _queue():
    from queue import Queue

    return Queue()
