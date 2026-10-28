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
    except (ImportError, OSError):
        return _report(
            "disconnected",
            "not_enumerated",
            None,
            "The microphone library is unavailable. The XVF3800 stays disconnected until PortAudio can open.",
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
            "ready",
            "processed_voice_stream",
            channels,
            None,
            device_index=found["index"],
            device_name=found["name"],
            note=(
                f"{found['name']} exposes {channels} processed channel(s), not 6 raw capsules. "
                "The dashboard classifies that mix with local shape rules. It is not an NVIDIA audio model."
            ),
        )
    return _report(
        "ready",
        "raw_6ch_assumed",
        channels,
        None,
        device_index=found["index"],
        device_name=found["name"],
        note="Four raw capsules are used. Loopback and the processed mix are discarded.",
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
    try:
        import sounddevice as sd
    except (ImportError, OSError) as exc:
        raise RuntimeError("The microphone library is unavailable.") from exc

    stream, _channels = _open_input(sd)
    indexes = mic_indexes()
    try:
        while not stop.is_set():
            try:
                payload, overflowed = stream.read(BLOCK_SAMPLES)
            except Exception:
                if stop.is_set():
                    break
                raise
            if overflowed:
                continue
            yield as_four_mics(payload, indexes)
    finally:
        stream.stop()
        stream.close()


def as_four_mics(block, indexes: tuple[int, int, int, int] | None = None):
    """Return float mics shaped (frames, 4). A 6-channel block keeps four capsules.

    A processed 1- or 2-channel mix is repeated across the four columns so the
    existing shape rules can run. Those copies are not separate capsules.
    """
    import numpy as np

    data = np.asarray(block)
    if data.ndim != 2:
        raise ValueError("expected an interleaved frame buffer shaped (frames, channels)")
    if data.shape[1] >= RAW_CHANNELS:
        return deinterleave_mics(data, indexes)
    column = data[:, :1]
    if np.issubdtype(column.dtype, np.integer):
        column = column.astype(np.float64) / 32768.0
    else:
        column = column.astype(np.float64)
    return np.repeat(column, 4, axis=1)


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
        candidates.append({
            "index": index,
            "name": name,
            "max_input_channels": int(item["max_input_channels"]),
            "default_samplerate": float(item["default_samplerate"]),
            "hostapi": int(item["hostapi"]),
        })
    if override:
        if override.isdigit():
            index = int(override)
            return next((item for item in candidates if item["index"] == index), None)
        narrowed = [item for item in candidates if override.lower() in item["name"].lower()]
        return max(narrowed, key=lambda item: item["max_input_channels"], default=None)
    named = [item for item in candidates if any(needle in item["name"].lower() for needle in _NAME_NEEDLES)]
    if not named:
        return None
    return min(named, key=_input_rank)


def _input_rank(item: dict) -> tuple:
    # WASAPI, then DirectSound, then MME. WDM-KS fails to start on this array.
    host_penalty = {2: 0, 1: 1, 0: 2}.get(int(item.get("hostapi", -1)), 5)
    return (
        -int(item["max_input_channels"]),
        host_penalty,
        abs(float(item["default_samplerate"]) - RATE_HZ),
        int(item["index"]),
    )


def _open_input(sd):
    """Start one input stream. Try every ReSpeaker endpoint until one accepts reads."""
    override = os.environ.get("RUBBLEECHO_AUDIO_DEVICE", "").strip()
    devices = sd.query_devices()
    named = []
    for index, item in enumerate(devices):
        if int(item["max_input_channels"]) < 1:
            continue
        name = str(item["name"])
        if override:
            if override.isdigit() and int(override) != index:
                continue
            if not override.isdigit() and override.lower() not in name.lower():
                continue
        elif not any(needle in name.lower() for needle in _NAME_NEEDLES):
            continue
        named.append({
            "index": index,
            "name": name,
            "max_input_channels": int(item["max_input_channels"]),
            "default_samplerate": float(item["default_samplerate"]),
            "hostapi": int(item["hostapi"]),
        })
    errors = []
    for item in sorted(named, key=_input_rank):
        channels = min(int(item["max_input_channels"]), RAW_CHANNELS)
        stream = None
        try:
            stream = sd.InputStream(
                device=item["index"],
                channels=channels,
                samplerate=RATE_HZ,
                dtype="int16",
                blocksize=BLOCK_SAMPLES,
                latency="high",
            )
            stream.start()
            stream.read(BLOCK_SAMPLES)
            return stream, channels
        except Exception as exc:
            errors.append(f"{item['index']} {item['name']}: {exc}")
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass
    detail = "; ".join(errors) if errors else "XVF3800 was not enumerated."
    raise RuntimeError(detail)


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
    note: str | None = None,
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
        "note": note,
        "status": "READY" if state == "ready" else "NEEDS_HARDWARE_VERIFICATION",
        "piezo": False,
    }


def _queue():
    from queue import Queue

    return Queue()
