"""When a live signal arrives, ask the vision model and the reasoning model.

Neither call commands the rover.
"""

from __future__ import annotations

import os
import threading

from app.services.sensor_gates import enabled

_lock = threading.Lock()
_running = False


def schedule_review() -> None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        _review()
        return
    thread = threading.Thread(target=_guarded, name="signal-review", daemon=True)
    thread.start()


def _guarded() -> None:
    global _running
    with _lock:
        if _running:
            return
        _running = True
    try:
        _review()
    finally:
        with _lock:
            _running = False


def _review() -> None:
    try:
        _review_body()
    except Exception as exc:
        from app.services.clock import utc_now
        from app.state import get_state

        get_state().add_event(
            device="nebius_nvidia",
            sensor="reasoning",
            summary=f"Signal review failed ({type(exc).__name__}). Motors were not commanded.",
            quality="unavailable",
            captured_at_utc=utc_now(),
            value=None,
            unit=None,
        )


def _review_body() -> None:
    from app.ai.nebius_client import vision_live
    from app.services.clock import utc_now
    from app.services.pi_ingest import posted_frame
    from app.services.search_plan import _signal_kind, apply_signal
    from app.state import get_state

    state = get_state()
    if _signal_kind(state) is None:
        return
    frame = posted_frame("camera_top") if enabled("camera") else None
    if frame:
        seen = vision_live(frame, "image/jpeg", "Frame stored with this signal. Do not command the rover.")
        if seen.get("ok"):
            state.scene_note = seen.get("scene")
            state.add_event(
                device="camera_top",
                sensor="vision",
                summary="Vision model described the stored frame. Motors were not commanded.",
                quality="advisory",
                captured_at_utc=utc_now(),
                value=None,
                unit=None,
            )
    result = apply_signal()
    state.add_event(
        device="nebius_nvidia",
        sensor="reasoning",
        summary=f"{result.get('message', 'Signal reviewed.')} Motors were not commanded.",
        quality="advisory",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
    )
