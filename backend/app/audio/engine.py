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
    def __init__(self, calibration: AcousticCalibration | None = None, source_mode: str = "dummy", channel_note: str | None = None) -> None:
        self.calibration = calibration or AcousticCalibration()
        self.source_mode = source_mode
        self.channel_note = channel_note or "4 raw mic channels. Processed mix and loopback are not used. No piezo in this path."
        self.filter = StreamingBandpass()
        self.hops = HopAnalyzer()
        self.tracker = EventTracker(self.calibration, source_mode=source_mode)
        self._recent = np.zeros(0, dtype=np.float64)
        self._last: dict | None = None

    def push(self, mics: np.ndarray) -> list[dict]:
        filtered = self.filter.process(mics)
        self._remember(filtered)
        events = []
        for features in self.hops.push(filtered):
            self._last = features
            for event in self.tracker.feed(features):
                events.append(self._decorate(event))
        return events

    def finish(self) -> list[dict]:
        return [self._decorate(event) for event in self.tracker.finish()]

    def listening_view(self) -> dict:
        rms = float(np.sqrt(np.mean(self._recent * self._recent))) if self._recent.size else 0.0
        level = None if rms <= 1e-12 else float(20.0 * np.log10(rms))
        return {
            "class": self._live_class(),
            "rms_dbfs": level,
            "peak_dbfs": None,
            "model_score": None,
            "score_semantics": "local_shape_rules_not_nvidia",
            "origin_unknown": True,
            "site_id": None,
            "source_mode": self.source_mode,
            "duration_ms": 0.0,
            "onset": False,
            "channel": None if self._last is None else self._last.get("channel"),
            "tdoa": None,
            "tdoa_summary": "no completed impulse in this hop",
            "channel_note": self.channel_note,
            "training_status": self.calibration.training_status,
            "hardware_calibrated": False,
            "limitations": [
                "thresholds_fit_on_synthetic_array_clips",
                "no_piezo_veto",
                "not_an_nvidia_audio_model",
            ],
        }

    def _live_class(self) -> str:
        features = self._last
        if features is None:
            return "listening"
        floor = self.tracker._floor()
        if floor is None:
            return "listening"
        rms = float(features["rms"])
        rise = rms / max(floor, 1e-8)
        cal = self.calibration
        if rise >= cal.rise_ratio and float(features["crest"]) >= cal.crest_min:
            return "knock"
        if (
            float(features["flatness"]) >= cal.flatness_min
            and float(features["band_fraction"]) >= cal.band_fraction_min
            and rise >= cal.scratch_rms_ratio
            and float(features["crest"]) < cal.crest_min
        ):
            return "scratch/scrape"
        if rise < 1.8:
            return "silence"
        return "ambient"

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
    from app.services.sensor_gates import enabled

    global _THREAD
    if not enabled("acoustic"):
        return {"ok": False, "message": "Acoustic measuring is off."}
    report = device_report()
    if report["state"] != "ready":
        _mark_device(report, streaming=False)
        return {
            "ok": False,
            "message": report["error"] or "XVF3800 raw stream is not available.",
            "report": report,
        }
    processed = report.get("firmware_mode") == "processed_voice_stream"
    with _LISTEN_LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            return {"ok": True, "message": "Already listening on the XVF3800.", "report": report}
        _STOP.clear()
        _THREAD = threading.Thread(target=_listen_loop, args=(report,), name="xvf3800-listen", daemon=True)
        _THREAD.start()
    if processed:
        message = "Listening to the USB processed mix at 16000 Hz. Local shape rules label silence, ambient, knock, or scratch. This is not an NVIDIA audio model."
    else:
        message = "Listening on 4 raw channels at 16000 Hz. Local shape rules label the sound. Processed mix discarded. No piezo."
    return {"ok": True, "message": message, "report": report}


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

    note = report.get("note") or "Live microphone. Local shape rules, not an NVIDIA audio model."
    engine = AcousticEngine(load_calibration(), source_mode="live", channel_note=note)
    started = False
    try:
        for block in iter_mic_blocks(_STOP):
            if not started:
                _mark_device(report, streaming=True)
                started = True
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
    from app.services.mic_window import publish_allowed
    from app.state import get_state

    if not publish_allowed():
        return
    state = get_state()
    public = {key: value for key, value in acoustic.items() if key != "frame"}
    from app.services.briefing import sound_category

    label = public.get("class") if isinstance(public.get("class"), str) else None
    public["sound_category"] = sound_category(label)
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
            device["quality"] = "processed_2ch" if report.get("firmware_mode") == "processed_voice_stream" else "raw_6ch"
            device["error"] = None
        else:
            device["state"] = "disconnected"
            device["source_mode"] = "unavailable"
            device["quality"] = "not_enumerated"
            device["error"] = report.get("error") or "USB audio device is not opened."

