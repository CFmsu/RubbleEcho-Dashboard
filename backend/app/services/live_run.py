"""Live session for Raspberry Pi samples. It does not load scripted sensor cases."""

import time
from datetime import datetime, timezone

from app.config.geometry import search_lattice
from app.services.clock import utc_now
from app.services.mission import _sync_trial, _trial_shell
from app.state import get_state


def open_pi_session() -> dict:
    """Wait for posted Pi samples. Wheels stay still."""
    from app.services.pi_mimic import stop_mimic
    from app.services.sim_run import cancel_run

    stop_mimic()
    cancel_run()
    state = get_state()
    state.reset()
    state.mode = "live"
    state.phase = "SCANNING"
    state.safety = "HOLD"
    state.run_active = True
    state.scan_stage = "WAIT_PI"
    state.run_started = time.monotonic()
    state.run_elapsed_s = 0.0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    state.trial_id = f"live-{stamp}"
    state.trial = _trial_shell(state.trial_id, "live")
    state.trial["media_files"] = []
    state.scan_route = search_lattice()
    state.add_event(
        device="raspberry_pi_4",
        sensor="link",
        summary="Waiting for Raspberry Pi samples. Scripted sensor cases are not loaded.",
        quality="live",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
    )
    _sync_trial(state)
    return {
        "ok": True,
        "status": 200,
        "mode": "LIVE",
        "trial_id": state.trial_id,
        "motion": "not_authorized",
    }


def authorize_motion() -> dict:
    """Stay stopped on the first square and sample each sensor in turn."""
    from app.drivers.motor_link import transmit
    from app.services.auto_listen import start

    state = get_state()
    if state.mode != "live" or not state.run_active:
        opened = open_pi_session()
        if not opened["ok"]:
            return opened
        state = get_state()
    link = transmit("S")
    state.add_event(
        device="arduino_uno",
        sensor="motors",
        summary="Armed. The rover stays on row 1, the first square, while the sensors take a turn.",
        quality="operator",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
    )
    started = start()
    _sync_trial(state)
    return {
        "ok": True,
        "status": 200,
        "mode": "LIVE",
        "trial_id": state.trial_id,
        "motion": "stopped",
        "drive_mode": "auto",
        "sensors": started,
        "rover": link,
    }
