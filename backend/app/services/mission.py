import os
import subprocess
import time
from datetime import datetime, timezone

from app.ai.nebius_client import ai_status, reason_live
from app.config.geometry import known_point_ids, load_geometry
from app.config.settings import ai_enabled
from app.drivers.camera_pi import find_camera
from app.persistence.store import load_trial, save_trial
from app.services.briefing import align_narrative
from app.services.export_trial import build_export
from app.services.fusion import local_assessment
from app.services.policy import on_cloud_failure, on_link_lost, vet_command
from app.services.replay import load_replay
from app.services.snapshot import build_snapshot
from app.state import LIMITATIONS, get_state
from app.version import APP_VERSION


def snapshot() -> dict:
    return build_snapshot(get_state())


def note_legacy_start() -> None:
    state = get_state()
    state.legacy_active = True
    if state.mode in {"unavailable", "simulation"}:
        state.mode = "simulation"


def note_legacy_reset() -> None:
    state = get_state()
    state.legacy_active = False
    if state.mode == "simulation":
        state.mode = "unavailable"
        state.phase = "IDLE"


def start_trial(mode: str, fixture: str | None) -> dict:
    state = get_state()
    if mode == "simulation":
        return {
            "ok": False,
            "status": 409,
            "error": "Use POST /api/mission/demo for the legacy grid simulation.",
        }
    if mode == "live":
        from app.services.live_run import open_pi_session

        return open_pi_session()
    if mode != "replay":
        return {"ok": False, "status": 400, "error": "unsupported mode"}
    if fixture not in {None, "sample_trial"}:
        return {"ok": False, "status": 404, "error": "unknown fixture"}
    state.reset()
    try:
        load_replay(state, "sample_trial")
    except FileNotFoundError:
        return {"ok": False, "status": 404, "error": "fixture missing"}
    trial_id = "trial_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    state.trial_id = trial_id
    state.trial = _trial_shell(trial_id, "replay")
    _sync_trial(state)
    return {"ok": True, "status": 200, "trial_id": trial_id, "mode": "replay"}


def estop(reason: str = "operator_estop") -> dict:
    from app.services.sim_run import cancel_run

    cancel_run()
    from app.services.remote_drive import hold_stopped
    from app.drivers.motor_link import transmit

    hold_stopped()
    transmit("S")
    state = get_state()
    state.run_active = False
    state.scan_stage = "IDLE"
    state.phase = "ESTOP"
    state.safety = "ESTOP"
    state.solenoid.disarm()
    _solenoid_stop()
    if state.legacy_active:
        import simulation

        simulation.pause_mission()
    event = state.add_event(
        device="safety",
        sensor="safety",
        summary=f"STOP {reason}. Solenoid disarmed. Pin A0 driven low when the Arduino port is open.",
        quality="safety",
        captured_at_utc=None,
        value=None,
        unit=None,
    )
    _sync_trial(state)
    return {
        "safety_state": state.safety,
        "mission_phase": state.phase,
        "output_energized": False,
        "event_id": event["event_id"],
    }


def hold(reason: str = "operator_stop") -> dict:
    from app.services.remote_drive import hold_stopped
    from app.drivers.motor_link import transmit

    hold_stopped()
    transmit("S")
    state = get_state()
    if state.phase != "ESTOP":
        state.safety = "STOP"
        state.phase = "FAULT"
    state.solenoid.disarm()
    _solenoid_stop()
    if state.legacy_active:
        import simulation

        simulation.pause_mission()
    state.add_event(
        device="safety",
        sensor="safety",
        summary=f"Hold {reason}.",
        quality="safety",
        captured_at_utc=None,
        value=None,
        unit=None,
    )
    _sync_trial(state)
    return {"safety_state": state.safety, "mission_phase": state.phase, "output_energized": False}


def apply_link_lost() -> dict:
    state = get_state()
    decision = on_link_lost(state.mode)
    state.operator_link = False
    if decision["disarm"]:
        state.safety = decision["safety"]
        state.phase = decision["phase"]
        state.solenoid.disarm()
        _solenoid_stop()
        state.add_event(
            device="safety",
            sensor="safety",
            summary="Operator link lost during live mode. STOP and disarm.",
            quality="safety",
            captured_at_utc=None,
            value=None,
            unit=None,
        )
    return decision


def submit_command(command: dict) -> dict:
    state = get_state()
    context = _motion_context(state)
    if command.get("target_x_cm") is not None:
        context["target_x_cm"] = command["target_x_cm"]
        context["target_y_cm"] = command["target_y_cm"]
    decision = vet_command(command, context, state.seen_command_ids)
    command_id = command.get("command_id")
    if isinstance(command_id, str) and command_id:
        state.seen_command_ids.add(command_id)
    decision["transmitted"] = False
    decision["execute_hardware"] = False
    state.command_log.append({"command": command, "decision": decision})
    if decision.get("disarm") or decision.get("hard_stop"):
        state.solenoid.disarm()
        _solenoid_stop()
        state.safety = "STOP"
        if state.phase != "ESTOP":
            state.phase = "FAULT"
    elif decision.get("safety") == "STOP":
        state.safety = "STOP"
    state.add_event(
        device="safety",
        sensor="command",
        summary="Command "
        + str(command.get("type"))
        + " "
        + ",".join(decision.get("reasons") or ["logged"]),
        quality="rejected" if not decision.get("accepted") else "not_transmitted",
        captured_at_utc=None,
        value=None,
        unit=None,
    )
    _sync_trial(state)
    return decision


def knock_request(width_ms: int, consent: bool, rover_moving: bool, now_ms: int) -> dict:
    from app.drivers.solenoid_link import transmit

    state = get_state()
    result = state.solenoid.request_pulse(width_ms, rover_moving, now_ms, consent)
    link = {"sent": False, "port": None, "command": "KNOCK", "reason": "not_sent"}
    if result["accepted"]:
        link = transmit("KNOCK")
        _mark_solenoid(link)
        if link["sent"]:
            result["reason"] = "sent"
    if result["state"] == "FAULT":
        state.safety = "STOP"
        state.phase = "FAULT"
    result["link"] = link
    if link["sent"]:
        summary = (
            f"Knock sent to {link['port']}. Pin A0, three taps, "
            f"{state.solenoid.PULSE_MS} ms on and {state.solenoid.GAP_MS} ms off."
        )
        quality = "transmitted"
    else:
        summary = f"Knock request {result['reason']}."
        quality = "not_transmitted"
    state.add_event(
        device="solenoid",
        sensor="solenoid",
        summary=summary,
        quality=quality,
        captured_at_utc=None,
        value=width_ms,
        unit="ms",
    )
    _sync_trial(state)
    return result


def _solenoid_stop() -> dict:
    from app.drivers.solenoid_link import transmit

    link = transmit("STOP")
    if link["sent"]:
        _mark_solenoid(link)
    return link


def _mark_solenoid(link: dict) -> None:
    state = get_state()
    for device in state.devices:
        if device["device_id"] != "solenoid":
            continue
        device["firmware"] = "arduino_solenoid"
        device["driver"] = "pyserial"
        device["last_seen_utc"] = None
        if link.get("sent"):
            device["state"] = "connected"
            device["source_mode"] = "live"
            device["quality"] = "serial_command"
            device["error"] = None
        else:
            device["error"] = link.get("reason") or "arduino_not_found"


def arm_solenoid(consent: bool) -> dict:
    return get_state().solenoid.arm(consent)


def request_reason() -> dict:
    state = get_state()
    now = time.monotonic()
    if state.reasoning is not None and now - state.last_ai_monotonic < 5:
        return {"ok": False, "kind": "rate_limited", "reasoning": state.reasoning}
    state.last_ai_monotonic = now
    status = ai_status()
    live_enabled = ai_enabled()
    if status["status"] == "NOT_CONFIGURED" or not live_enabled:
        result = local_assessment(state.events, state.heatmap)
        if status["status"] != "NOT_CONFIGURED" and not live_enabled:
            result["validation_status"] = "live_call_disabled"
            result["summary"] = (
                "Model id is configured, but RUBBLEECHO_AI_LIVE is not 1, so no Token Factory call was made. "
                + result["summary"]
            )
        state.reasoning = _spoken(result)
        _sync_trial(state)
        return {"ok": True, "reasoning": state.reasoning, "nvidia_online": False}
    known = set(known_point_ids())
    for cell in state.scan_route or []:
        known.add(str(cell.get("id")))
    for point in state.heatmap or []:
        if point.get("point_id"):
            known.add(str(point["point_id"]))
    live = reason_live(
        _evidence(state),
        {event["event_id"] for event in state.events},
        known,
        state.search_plan,
        _cell_briefs(state),
    )
    return apply_model_result(live)


def apply_model_result(live: dict) -> dict:
    state = get_state()
    if not live.get("ok"):
        failure = on_cloud_failure(str(live.get("kind") or "provider_error"))
        state.safety = failure["safety"]
        state.phase = failure["phase"]
        state.solenoid.disarm()
        _solenoid_stop()
        result = local_assessment(state.events, state.heatmap)
        result["validation_status"] = failure["reason"]
        result["unknowns"] = [failure["reason"], *result["unknowns"]]
        result["nvidia_online"] = False
        state.reasoning = _spoken(result)
        state.add_event(
            device="nebius_nvidia",
            sensor="reasoning",
            summary=f"Model call failed ({failure['reason']}). Motion held and solenoid disarmed.",
            quality="error",
            captured_at_utc=None,
            value=None,
            unit=None,
        )
        _sync_trial(state)
        return {"ok": False, "kind": failure["reason"], "reasoning": result, "nvidia_online": False}
    state.reasoning = _spoken(live["result"])
    _sync_trial(state)
    return {"ok": True, "reasoning": state.reasoning, "nvidia_online": True}


def _spoken(result: dict) -> dict:
    point = None
    recommendation = result.get("recommendation")
    if isinstance(recommendation, dict):
        point = recommendation.get("point_id")
    state = get_state()
    heatmap = _grid_points(state)
    result["narrative"] = align_narrative(
        result.get("narrative") if isinstance(result.get("narrative"), str) else None,
        heatmap,
        str(point) if point else None,
    )
    from app.services.observation import attach_to_reasoning

    attach_to_reasoning(state, result)
    return result


def annotate(trial_id: str, fields: dict) -> dict | None:
    state = get_state()
    trial = state.trial if state.trial and state.trial_id == trial_id else load_trial(trial_id)
    if trial is None:
        return None
    for key in ("sand_depth", "cover_depth_cm", "operator_label", "notes"):
        if key in fields:
            trial[key] = fields[key]
    if "actual_source" in fields and fields["actual_source"]:
        trial["actual_source"] = fields["actual_source"]
    trial["actual_source_disclosed"] = bool(fields.get("release_to_overlay"))
    if state.trial_id == trial_id:
        state.trial = trial
    save_trial(trial)
    return {
        "trial_id": trial_id,
        "actual_source_recorded": trial.get("actual_source") != "not_recorded",
        "released_to_overlay": trial["actual_source_disclosed"],
    }


def ground_truth(trial_id: str) -> dict | None:
    state = get_state()
    trial = state.trial if state.trial and state.trial_id == trial_id else load_trial(trial_id)
    if trial is None:
        return None
    if not trial.get("actual_source_disclosed"):
        return {"disclosed": False, "actual_source": None}
    return {"disclosed": True, "actual_source": trial.get("actual_source")}


def export_trial(trial_id: str) -> bytes | None:
    state = get_state()
    trial = state.trial if state.trial and state.trial_id == trial_id else load_trial(trial_id)
    if trial is None:
        return None
    if state.trial_id == trial_id:
        _sync_trial(state)
        trial = state.trial or trial
    return build_export(trial, _git_sha(), _simulation_files(trial))


def capture_camera(camera_id: str) -> dict:
    from app.services.pi_ingest import posted_frame

    camera = find_camera(camera_id, get_state().cameras)
    if camera is None:
        return {"ok": False, "status": 404, "error": "unknown camera"}
    frame = posted_frame(camera_id)
    if frame is None:
        return {
            "ok": False,
            "status": 409,
            "error": "No frame has been posted by the Raspberry Pi for this camera.",
            "state": camera["state"],
            "frame_available": False,
        }
    return {
        "ok": True,
        "status": 200,
        "state": "connected",
        "frame_available": True,
        "byte_length": len(frame),
        "media_type": "image/jpeg",
    }


def _motion_context(state) -> dict:
    ultrasonic = state.ultrasonic or {}
    pose = state.pose or {}
    return {
        "echo_timeout": ultrasonic.get("echo_timeout", True) if state.ultrasonic else True,
        "distance_cm": ultrasonic.get("distance_cm") if state.ultrasonic else None,
        "pose_valid": bool(pose.get("valid")) if state.pose else False,
        "pose_age_ms": 0 if state.pose else 10**9,
        "heading_deg": pose.get("heading_deg") if state.pose else None,
        "encoder_fresh": False,
        "mode": state.mode,
        "operator_link": state.operator_link,
    }


def _evidence(state) -> list[dict]:
    rows = []
    for event in state.events:
        if event.get("sensor") not in {"acoustic", "piezo", "radar", "ultrasonic"}:
            continue
        rows.append(
            {
                "event_id": event["event_id"],
                "sensor": event.get("sensor"),
                "summary": event.get("summary"),
                "value": event.get("value"),
                "unit": event.get("unit"),
                "site_id": event.get("site_id"),
                "quality": event.get("quality"),
                "mode": event.get("mode"),
            }
        )
    by_site: dict[str, dict] = {}
    order: list[str] = []
    for row in rows:
        site = str(row.get("site_id") or row["event_id"])
        previous = by_site.get(site)
        if previous is None:
            order.append(site)
            by_site[site] = row
        elif row.get("sensor") == "acoustic" or previous.get("sensor") != "acoustic":
            by_site[site] = row
    if by_site:
        return [by_site[site] for site in order][-36:]
    return rows[-36:]


def _grid_points(state) -> list[dict]:
    captures = list(getattr(state, "cell_captures", None) or [])
    if captures:
        return captures
    return list(state.heatmap or [])


def _cell_briefs(state) -> list[dict]:
    briefs = []
    for point in _grid_points(state):
        readings = point.get("readings") if isinstance(point.get("readings"), dict) else {}
        briefs.append(
            {
                "point_id": point.get("point_id"),
                "place": readings.get("place"),
                "sound": readings.get("sound"),
                "sound_category": readings.get("sound_category"),
                "radar_presence": readings.get("radar_presence"),
                "distance_m": readings.get("distance_m"),
                "ultrasonic_cm": readings.get("ultrasonic_cm"),
                "photos": readings.get("photos"),
                "opencv": readings.get("opencv"),
                "vision": readings.get("vision"),
                "reading_score": point.get("score"),
            }
        )
    briefs.sort(key=lambda item: -(item["reading_score"] or 0))
    return briefs


def _trial_shell(trial_id: str, mode: str) -> dict:
    geometry = load_geometry()
    return {
        "trial_id": trial_id,
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": mode,
        "operator_label": "",
        "drawing_revision": geometry["drawing"]["revision"],
        "sand_depth": None,
        "cover_depth_cm": None,
        "actual_source": "not_recorded",
        "actual_source_disclosed": False,
        "geometry_revision": geometry["geometry_revision"],
        "calibration_id": None,
        "motor_state": "not_connected",
        "notes": "",
        "events": [],
        "samples": [],
        "reasoning": None,
        "limitations": list(LIMITATIONS),
        "app_version": APP_VERSION,
    }


def _sync_trial(state) -> None:
    if not state.trial:
        return
    state.trial["events"] = list(state.events)
    state.trial["samples"] = list(state.samples)
    state.trial["reasoning"] = state.reasoning
    state.trial["mode"] = state.mode
    save_trial(state.trial)


def _simulation_files(trial: dict) -> dict[str, bytes]:
    from app.persistence.store import data_dir

    trial_id = trial.get("trial_id")
    if trial.get("mode") != "simulation" or not trial_id:
        return {}
    root = (data_dir() / "sim_media" / str(trial_id)).resolve()
    files: dict[str, bytes] = {}
    for name in trial.get("media_files") or []:
        if not isinstance(name, str) or name.startswith("/") or ".." in name or "\\" in name:
            continue
        path = (root / name).resolve()
        if root not in path.parents or not path.is_file():
            continue
        files[name] = path.read_bytes()
    return files


def _git_sha() -> str:
    try:
        from app.paths import REPO_ROOT

        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
