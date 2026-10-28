"""Open the microphone for one stopped listen, then close it.

The Uno already waits 7 seconds in each square. The trace is shown only
during that stop. Samples taken while the rover is moving are not shown.
"""

from __future__ import annotations

import os
import threading

DWELL_S = 7.0

_lock = threading.Lock()
_timer: threading.Timer | None = None
_showing = True
_cell: dict | None = None


def publish_allowed() -> bool:
    with _lock:
        return _showing


def reset_window() -> None:
    global _showing, _cell
    _cancel()
    with _lock:
        _showing = True
        _cell = None


def grid_started() -> None:
    """A new run begins with the microphone off until the first full stop."""
    hide_while_moving()


def begin_hold(cell: dict, *, dwell_s: float = DWELL_S, use_hardware: bool | None = None) -> None:
    """Turn the microphone on for this square, then off after the stop."""
    hardware = (not os.environ.get("PYTEST_CURRENT_TEST")) if use_hardware is None else use_hardware
    if not hardware:
        from app.services.cell_visit import note_hold

        note_hold(cell)
        return
    global _cell, _showing
    _cancel()
    with _lock:
        _cell = cell
        _showing = True
    _clear_display()
    _mark_listening(True)
    _start_mic()
    timer = threading.Timer(dwell_s, _commit_keep)
    timer.daemon = True
    timer.name = "mic-window"
    with _lock:
        global _timer
        _timer = timer
    timer.start()


def hide_while_moving() -> None:
    """The wheels are turning. Keep the saved listen and blank the live trace."""
    _commit(clear=True)


def grid_finished() -> None:
    """The route is over. Close the microphone and leave the last stop on screen."""
    _commit(clear=False)


def _commit_keep() -> None:
    _commit(clear=False)


def _commit(clear: bool) -> None:
    global _cell, _showing
    with _lock:
        cell = _cell
        _cell = None
        _showing = False
        _cancel()
    if cell is not None:
        from app.services.cell_visit import note_hold

        note_hold(cell)
    _mark_listening(False)
    _stop_mic()
    if clear:
        _clear_display()


def _cancel() -> None:
    global _timer
    timer = _timer
    _timer = None
    if timer is not None:
        timer.cancel()


def _mark_listening(on: bool) -> None:
    from app.state import get_state

    state = get_state()
    if on:
        state.phase = "LISTEN"
        return
    if state.phase == "LISTEN":
        state.phase = "SCANNING"


def _clear_display() -> None:
    from app.state import get_state

    state = get_state()
    state.acoustic = None
    state.acoustic_envelope = []
    state.acoustic_waveform = []


def _start_mic() -> None:
    from app.audio.engine import start_listener
    from app.services.sensor_gates import set_gate

    set_gate("acoustic", True)
    start_listener()


def _stop_mic() -> None:
    if threading.current_thread().name == "rover-track":
        threading.Thread(target=_stop_mic_now, name="mic-off", daemon=True).start()
        return
    _stop_mic_now()


def _stop_mic_now() -> None:
    from app.services.sensor_gates import set_gate

    set_gate("acoustic", False)
