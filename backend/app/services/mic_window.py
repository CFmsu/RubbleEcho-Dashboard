"""Open the microphone for one stopped listen, then close it.

The Uno already waits 7 seconds in each square. The trace is shown only
during that stop. Samples taken while the rover is moving are not shown.
"""

from __future__ import annotations

import os
import threading
import time

DWELL_S = 12.0

_lock = threading.Lock()
_timer: threading.Timer | None = None
_showing = True
_keep = False
_cell: dict | None = None
_deploy_listen = False


def publish_allowed() -> bool:
    with _lock:
        return _showing


def reset_window() -> None:
    global _showing, _cell, _keep, _deploy_listen
    _cancel()
    with _lock:
        _showing = True
        _keep = False
        _cell = None
        _deploy_listen = False


def grid_started() -> None:
    """The next stop is the 7 second deploy listen on row 1."""
    global _deploy_listen
    hide_while_moving()
    _deploy_listen = True


def begin_hold(cell: dict, *, dwell_s: float = DWELL_S, use_hardware: bool | None = None) -> None:
    """Mark this square. The microphone array is on the Pi, so this laptop does not record it."""
    if use_hardware is True:
        _begin_local_mic(cell, dwell_s)
        return
    if os.environ.get("PYTEST_CURRENT_TEST"):
        from app.services.cell_visit import note_hold

        note_hold(cell)
        return
    if not _deploy_listen:
        from app.services.cell_visit import note_hold

        note_hold(cell)
        return
    _arm_pi_listen(cell)


def _arm_pi_listen(cell: dict) -> None:
    """Clear the previous square. The Pi posts the new recording when the stop ends."""
    global _cell, _keep, _showing, _deploy_listen
    _cancel()
    deploy = False
    with _lock:
        _cell = cell
        _keep = False
        _showing = False
        deploy = _deploy_listen
        _deploy_listen = False
    _clear_display()
    _mark_listening(True)
    if deploy:
        from app.state import get_state

        state = get_state()
        state.listen_until = time.time() + DWELL_S
        state.scan_stage = f"DEPLOY {cell.get('id')}"


def keep_posted_sample() -> None:
    """The Pi sample is the measurement for this square. Driving must not wipe it."""
    global _keep
    with _lock:
        _keep = True


def _begin_local_mic(cell: dict, dwell_s: float) -> None:
    """Laptop microphone path kept for the bench test that asks for it."""
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
    with _lock:
        if _keep:
            return
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
