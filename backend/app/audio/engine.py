"""One pipeline for dummy clips and the live XVF3800 stream."""

from __future__ import annotations

import json
import threading

import numpy as np

from app.audio.detector import AcousticCalibration, EventTracker
from app.persistence.store import data_dir
from app.services.feature_extraction import HopAnalyzer, StreamingBandpass, display_waveform, envelope_dbfs
from app.services.fusion import gcc_phat_delays

_LISTEN_LOCK = threading.Lock()
_STOP = threading.Event()
_THREAD: threading.Thread | None = None


def load_calibration() -> AcousticCalibration:
    path = data_dir() / "acoustic_calibration.json"
    if not path.exists():
        return AcousticCalibration()
    return AcousticCalibration.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_calibration(calibration: AcousticCalibration, report: dict) -> str:
    path = data_dir() / "acoustic_calibration.json"
    payload = {"calibration": calibration.to_dict(), "report": report}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


class AcousticEngine:
    def __init__(self, calibration: AcousticCalibration | None = None, source_mode: str = "dummy") -> None:
        self.calibration = calibration or AcousticCalibration()
        self.source_mode = source_mode
        self.filter = StreamingBandpass()
        self.hops = HopAnalyzer()
        self.tracker = EventTracker(self.calibration, source_mode=source_mode)
        self._recent = np.zeros(0, dtype=np.float64)

    def push(self, mics: np.ndarray) -> list[dict]:
        filtered = self.filter.process(mics)
        self._remember(filtered)
        events = []
        for features in self.hops.push(filtered):
            for event in self.tracker.feed(features):
                events.append(self._decorate(event))
        return events

    def finish(self) -> list[dict]:
        return [self._decorate(event) for event in self.tracker.finish()]

    def listening_view(self) -> dict:
        rms = float(np.sqrt(np.mean(self._recent * self._recent))) if self._recent.size else 0.0
        level = None if rms <= 1e-12 else float(20.0 * np.log10(rms))
        return {
            "class": "listening",
            "rms_dbfs": level,
            "peak_dbfs": None,
            "model_score": None,
            "score_semantics": "shape_rule_on_synthetic_calibration",
            "origin_unknown": True,
            "site_id": None,
            "source_mode": self.source_mode,
            "duration_ms": 0.0,
            "onset": False,
            "channel": None,
            "tdoa": None,
            "tdoa_summary": "no impulse in this hop",
            "channel_note": "4 raw mic channels. Processed mix and loopback are not used. No piezo in this path.",
            "training_status": self.calibration.training_status,
            "hardware_calibrated": False,
            "limitations": [
                "thresholds_fit_on_synthetic_array_clips",
                "no_piezo_veto",
                "requires_raw_6_channel_firmware",
            ],
        }

    def envelope(self) -> list[float]:
        if self._recent.size == 0:
            return []
        return envelope_dbfs(self._recent[-1600:].tolist())

    def waveform(self) -> list[float]:
        if self._recent.size == 0:
            return []
        return display_waveform(self._recent[-1600:].tolist())

    def _remember(self, filtered: np.ndarray) -> None:
        loudest = int(np.argmax(np.sqrt(np.mean(filtered * filtered, axis=0))))
        self._recent = np.concatenate((self._recent, filtered[:, loudest]))
        if self._recent.size > 1600:
            self._recent = self._recent[-1600:]

    def _decorate(self, event: dict) -> dict:
        frame = event.pop("frame", None)
        event["source_mode"] = self.source_mode
        if frame is not None and event["class"] in {"knock", "periodic_tapping"}:
            tdoa = gcc_phat_delays(frame, sample_rate=16000.0, max_lag=3)
            event["tdoa"] = {key: value for key, value in tdoa.items()}
            event["tdoa_summary"] = tdoa["summary"]
        else:
            event["tdoa"] = None
            event["tdoa_summary"] = "not an impulse"
        return event


def run_mics(samples: np.ndarray, calibration: AcousticCalibration | None = None, source_mode: str = "dummy") -> list[dict]:
    engine = AcousticEngine(calibration, source_mode=source_mode)
    events = engine.push(np.asarray(samples, dtype=np.float64))
    events.extend(engine.finish())
    return events


def start_listener() -> dict:
    from app.drivers.respeaker import device_report

    global _THREAD
    report = device_report()
    if report["state"] != "ready":
        _mark_device(report, streaming=False)
        return {
            "ok": False,
            "message": report["error"] or "XVF3800 raw stream is not available.",
            "report": report,
        }
    with _LISTEN_LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            return {"ok": True, "message": "Already listening on the XVF3800.", "report": report}
        _STOP.clear()
        _THREAD = threading.Thread(target=_listen_loop, args=(report,), name="xvf3800-listen", daemon=True)
        _THREAD.start()
    return {
        "ok": True,
        "message": "Listening on 4 raw channels at 16000 Hz. Processed mix discarded. No piezo.",
        "report": report,
    }


def stop_listener() -> dict:
    _STOP.set()
    thread = _THREAD
    if thread is not None and thread.is_alive() and threading.current_thread() is not thread:
        thread.join(timeout=2.0)
    from app.drivers.respeaker import device_report

    report = device_report()
    _mark_device(report, streaming=False)
    return {"ok": True, "message": "Microphone stream stopped.", "report": report}


def _listen_loop(report: dict) -> None:
    from app.drivers.respeaker import iter_mic_blocks

    engine = AcousticEngine(load_calibration(), source_mode="live")
    _mark_device(report, streaming=True)
    _publish(engine.listening_view(), engine.envelope(), None, engine.waveform())
    try:
        for block in iter_mic_blocks(_STOP):
            events = engine.push(block)
            if events:
                for event in events:
                    _publish(event, engine.envelope(), event["class"], engine.waveform())
            else:
                _publish(engine.listening_view(), engine.envelope(), None, engine.waveform())
    except Exception as exc:
        failed = dict(report)
        failed["state"] = "disconnected"
        failed["error"] = f"Audio stream failed: {exc}"
        _mark_device(failed, streaming=False)
    else:
        for event in engine.finish():
            _publish(event, engine.envelope(), event["class"], engine.waveform())
        _mark_device(report, streaming=False)


def _publish(acoustic: dict, envelope: list[float], summary: str | None, waveform: list[float] | None = None) -> None:
    from app.services.clock import utc_now
    from app.state import get_state

    state = get_state()
    public = {key: value for key, value in acoustic.items() if key != "frame"}
    state.acoustic = public
    state.acoustic_envelope = envelope
    state.acoustic_waveform = list(waveform or [])
    if summary and public.get("class") in {"knock", "scratch/scrape", "periodic_tapping"}:
        state.impulse = public
        state.impulse_envelope = envelope
        state.add_event(
            device="xvf3800",
            sensor="acoustic",
            summary=f"{summary} on raw mic {public.get('channel')}",
            quality="shape_rule",
            captured_at_utc=utc_now(),
            value=public.get("duration_ms"),
            unit="ms",
            acoustic_class=summary,
        )


def _mark_device(report: dict, streaming: bool) -> None:
    from app.services.clock import utc_now
    from app.state import get_state

    state = get_state()
    seen = utc_now()
    for device in state.devices:
        if device["device_id"] != "xvf3800":
            continue
        device["firmware"] = report.get("firmware_mode")
        device["sampling_rate_hz"] = report.get("sample_rate_hz")
        device["driver"] = "sounddevice"
        device["last_seen_utc"] = seen
        device["age_ms"] = 0
        if streaming and report.get("state") == "ready":
            device["state"] = "connected"
            device["source_mode"] = "live"
            device["quality"] = "raw_6ch"
            device["error"] = None
        else:
            device["state"] = "disconnected"
            device["source_mode"] = "unavailable"
            device["quality"] = "not_enumerated"
            device["error"] = report.get("error") or "USB audio device is not opened."

