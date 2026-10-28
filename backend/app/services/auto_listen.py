"""Arm stays put, then each sensor is turned on in order and the sound is categorized."""

from __future__ import annotations

import os
import threading
import time

from app.services.clock import utc_now
from app.state import get_state

_ORDER = ("radar", "ultrasonic", "camera", "acoustic")
_LABEL = {
    "radar": "Radar",
    "ultrasonic": "Range",
    "camera": "Camera",
    "acoustic": "Mic",
}
_lock = threading.Lock()
_cancel = threading.Event()
_thread: threading.Thread | None = None
_step: str | None = None


def public_auto() -> dict:
    with _lock:
        return {"step": _step, "running": _thread is not None and _thread.is_alive()}


def cancel() -> None:
    global _step
    _cancel.set()
    with _lock:
        _step = None


def reset_auto() -> None:
    cancel()
    thread = _thread
    if thread is not None and thread.is_alive() and threading.current_thread() is not thread:
        thread.join(timeout=1.0)


def start() -> dict:
    """Sample in place. This does not send the grid start character."""
    global _thread
    from app.services.remote_drive import mark_auto

    mark_auto()
    _cancel.clear()
    if os.environ.get("PYTEST_CURRENT_TEST"):
        _run()
        return {"started": True, "motion": "stopped"}
    with _lock:
        if _thread is not None and _thread.is_alive():
            return {"started": True, "motion": "stopped"}
        _thread = threading.Thread(target=_run, name="auto-listen", daemon=True)
        _thread.start()
    return {"started": True, "motion": "stopped"}


def _run() -> None:
    global _step
    from app.config.geometry import search_lattice
    from app.services.cell_visit import note_hold, watch
    from app.services.sensor_gates import set_gate

    cell = search_lattice()[0]
    watch(str(cell["id"]))
    state = get_state()
    for name in _ORDER:
        if _cancel.is_set():
            return
        with _lock:
            _step = name
        set_gate(name, True)
        state.add_event(
            device="raspberry_pi_4",
            sensor=name,
            summary=f"{_LABEL[name]} on. The rover is still stopped.",
            quality="operator",
            captured_at_utc=utc_now(),
            value=None,
            unit=None,
            site_id=cell["id"],
        )
        if name == "radar":
            _sample_radar()
        elif name == "acoustic":
            _sample_acoustic()
        elif _cancel.wait(0.05 if os.environ.get("PYTEST_CURRENT_TEST") else 1.5):
            return
    if _cancel.is_set():
        return
    _categorize()
    note_hold(cell)
    with _lock:
        _step = "model"
    from app.services.mission import request_reason

    request_reason()
    with _lock:
        _step = "done"


def _sample_radar() -> None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    from app.services.radar_link import start_listener

    start_listener()
    _cancel.wait(2.0)


def _sample_acoustic() -> None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    from app.audio.engine import start_listener

    start_listener()
    deadline = time.monotonic() + 7.0
    while time.monotonic() < deadline and not _cancel.is_set():
        heard = get_state().acoustic or {}
        label = heard.get("class")
        if label not in {None, "listening"}:
            break
        _cancel.wait(0.25)


def _categorize() -> None:
    from app.services.briefing import sound_category

    state = get_state()
    heard = dict(state.acoustic or {})
    label = heard.get("class") if isinstance(heard.get("class"), str) else None
    heard["sound_category"] = sound_category(label)
    state.acoustic = heard
