"""Timed simulation walk with sample media and scripted sensor cases."""

import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from app.config.geometry import load_geometry
from app.drivers.piezo import piezo_features
from app.persistence.store import data_dir
from app.services.clock import utc_now
from app.services.feature_extraction import classify_window, envelope_dbfs
from app.services.mission import _sync_trial, _trial_shell
from app.services.sim_media import sample_png, sample_wav
from app.state import get_state

_lock = threading.Lock()
_timer: threading.Timer | None = None
_generation = 0
_index = 0
POINT_SECONDS = 5.0
SIMULATED_DEVICES = ("camera_top", "mr60bha2", "hc_sr04", "xvf3800", "piezo")

CASES = {
    "A_NEAR": {"audio": "knock", "piezo": 840, "distance_cm": 18.4, "presence": True, "range_m": 0.42, "bearing": -32, "case": "near_knock", "score": 0.84, "color": (232, 92, 92)},
    "A_FAR": {"audio": "knock", "piezo": 460, "distance_cm": 34.0, "presence": True, "range_m": 0.78, "bearing": -12, "case": "far_knock", "score": 0.58, "color": (214, 158, 70)},
    "B_NEAR": {"audio": "ambient", "piezo": 28, "distance_cm": 41.5, "presence": False, "range_m": None, "bearing": None, "case": "control_quiet", "score": 0.12, "color": (120, 150, 170)},
    "B_FAR": {"audio": "ambient", "piezo": 22, "distance_cm": 47.0, "presence": False, "range_m": None, "bearing": None, "case": "control_quiet", "score": 0.08, "color": (120, 150, 170)},
    "C_NEAR": {"audio": "scratch", "piezo": 210, "distance_cm": 26.5, "presence": True, "range_m": 0.55, "bearing": 24, "case": "weak_return", "score": 0.36, "color": (214, 158, 70)},
    "C_FAR": {"audio": "ambient", "piezo": 31, "distance_cm": 44.2, "presence": False, "range_m": None, "bearing": None, "case": "control_quiet", "score": 0.1, "color": (120, 150, 170)},
}


def start_run(schedule: bool = True) -> dict:
    global _index
    from app.services.radar_link import stop_radar

    stop_radar()
    cancel_run()
    state = get_state()
    state.reset()
    state.mode = "simulation"
    state.phase = "SCANNING"
    state.safety = "HOLD"
    state.run_active = True
    state.scan_stage = "CONNECT_CHECK"
    state.run_started = time.monotonic()
    state.run_elapsed_s = 0.0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    state.trial_id = f"sim-{stamp}"
    state.trial = _trial_shell(state.trial_id, "simulation")
    state.trial["media_files"] = []
    state.add_event(
        device="simulation",
        sensor="script",
        summary="Simulation started. Samples are scripted. Hardware is not connected.",
        quality="synthetic",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
    )
    _index = 0
    _sync_trial(state)
    if schedule:
        _arm(0.05)
    return {"ok": True, "status": 200, "mode": "SIMULATION", "trial_id": state.trial_id}


def advance_run() -> str | None:
    point_id = _publish()
    if point_id is None:
        return None
    if _index >= len(load_geometry()["measurement_points"]):
        _finish(get_state())
    return point_id


def halt_run() -> dict:
    state = get_state()
    was_running = state.run_active or state.mode == "simulation" or state.phase not in {"IDLE"}
    cancel_run()
    state.reset()
    if not was_running:
        return {
            "ok": True,
            "status": 200,
            "mission_phase": "IDLE",
            "message": "Already idle. Press Run to start the simulation.",
        }
    state.add_event(
        device="safety",
        sensor="safety",
        summary="Stopped. Simulation cleared. The console is idle.",
        quality="safety",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
    )
    return {"ok": True, "status": 200, "mission_phase": "IDLE", "message": "Stopped. The console is idle."}


def cancel_run() -> None:
    global _timer, _generation
    with _lock:
        _generation += 1
        if _timer is not None:
            _timer.cancel()
            _timer = None


def media_file(kind: str) -> Path | None:
    state = get_state()
    raw = state.media_camera if kind == "camera" else state.media_audio
    if not raw:
        return None
    path = Path(raw).resolve()
    root = (data_dir() / "sim_media").resolve()
    if root not in path.parents or not path.is_file():
        return None
    return path


def _publish() -> str | None:
    global _index
    state = get_state()
    if not state.run_active:
        return None
    points = load_geometry()["measurement_points"]
    if _index >= len(points):
        return None
    point = points[_index]
    case = CASES[point["id"]]
    _index += 1
    stamp = utc_now()
    state.scan_stage = str(point["id"])
    _mark_devices(state, stamp)
    _camera(state, point, case, stamp)
    _audio(state, point, case, stamp)
    _piezo(state, point, case, stamp)
    _ultrasonic(state, point, case, stamp)
    _radar(state, point, case, stamp)
    _pose(state, point, stamp)
    _record_sensor_events(state, point, stamp)
    event = state.add_event(
        device="simulation",
        sensor="script",
        summary=f"SIMULATION {point['id']} case {case['case']}. Scripted sample, not a live measurement.",
        quality="synthetic",
        captured_at_utc=stamp,
        value=case["distance_cm"],
        unit="cm",
        site_id=point["id"],
        acoustic_class=state.acoustic["class"] if state.acoustic else None,
    )
    state.heatmap = [item for item in state.heatmap if item["point_id"] != point["id"]]
    state.heatmap.append(
        {
            "point_id": point["id"],
            "x_cm": point["x_cm"],
            "y_cm": point["y_cm"],
            "score": case["score"],
            "score_semantics": "simulation_scenario_not_a_measurement",
            "interpolated": False,
            "sample_count": 1,
            "method": "scripted_case",
            "source_mode": "simulation",
            "quality": "synthetic",
            "evidence_event_ids": [event["event_id"]],
        }
    )
    _sync_trial(state)
    return str(point["id"])


def _camera(state, point: dict, case: dict, stamp: str) -> None:
    folder = data_dir() / "sim_media" / state.trial_id / "camera"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{point['id']}.png"
    path.write_bytes(sample_png(str(point["id"]), case["color"]))
    state.media_camera = str(path)
    name = f"camera/{point['id']}.png"
    if name not in state.trial["media_files"]:
        state.trial["media_files"].append(name)
    camera = state.cameras[0]
    camera.update(
        {
            "state": "simulated",
            "source_mode": "simulation",
            "fps": 1,
            "width": 320,
            "height": 180,
            "last_frame_utc": stamp,
            "error": None,
            "frame_available": True,
            "image_url": f"/api/simulation/camera.png?point={point['id']}",
        }
    )


def _audio(state, point: dict, case: dict, stamp: str) -> None:
    folder = data_dir() / "sim_media" / state.trial_id / "audio"
    folder.mkdir(parents=True, exist_ok=True)
    wav, samples = sample_wav(case["audio"])
    path = folder / f"{point['id']}.wav"
    path.write_bytes(wav)
    state.media_audio = str(path)
    name = f"audio/{point['id']}.wav"
    if name not in state.trial["media_files"]:
        state.trial["media_files"].append(name)
    acoustic = classify_window(samples[:1600], 16000, stamp, {"site_id": point["id"], "source_mode": "simulation"})
    acoustic["source_mode"] = "simulation"
    state.acoustic = acoustic
    state.acoustic_envelope = envelope_dbfs(samples[:1600])
    if acoustic["class"] in {"knock", "scratch/scrape"}:
        state.impulse = acoustic
        state.impulse_envelope = state.acoustic_envelope
    state.samples.append(
        {
            "captured_at_utc": stamp,
            "sensor": "xvf3800",
            "quantity": "acoustic_class",
            "value": acoustic["class"],
            "unit": "class",
            "quality": "synthetic",
            "mode": "simulation",
            "x_cm": point["x_cm"],
            "y_cm": point["y_cm"],
        }
    )


def _piezo(state, point: dict, case: dict, stamp: str) -> None:
    features = piezo_features([float(case["piezo"]), 0.0, 0.0], 1000, "scripted_contact", point["id"], False)
    features["source_mode"] = "simulation"
    state.piezo = features
    state.samples.append(
        {
            "captured_at_utc": stamp,
            "sensor": "piezo",
            "quantity": "peak_adc_counts",
            "value": features["peak_adc_counts"],
            "unit": "adc_counts",
            "quality": "synthetic",
            "mode": "simulation",
            "x_cm": point["x_cm"],
            "y_cm": point["y_cm"],
        }
    )


def _ultrasonic(state, point: dict, case: dict, stamp: str) -> None:
    state.ultrasonic = {
        "distance_cm": case["distance_cm"],
        "echo_timeout": False,
        "direction": "forward",
        "quality": "synthetic",
        "source_mode": "simulation",
        "valid": True,
    }
    state.samples.append(
        {
            "captured_at_utc": stamp,
            "sensor": "hc_sr04",
            "quantity": "obstacle_distance",
            "value": case["distance_cm"],
            "unit": "cm",
            "quality": "synthetic",
            "mode": "simulation",
            "x_cm": point["x_cm"],
            "y_cm": point["y_cm"],
        }
    )


def _radar(state, point: dict, case: dict, stamp: str) -> None:
    state.radar = {
        "human_presence": case["presence"],
        "distance_m": case["range_m"],
        "breath_rate_bpm": 16.0 if case["presence"] else 0.0,
        "heart_rate_bpm": 74.0 if case["presence"] else 0.0,
        "num_targets": 1 if case["presence"] else 0,
        "illuminance_lx": 140.0,
        "breath_phase": None,
        "heart_phase": None,
        "total_phase": None,
        "distance_unit": "m" if case["range_m"] is not None else None,
        "distance_reported": case["range_m"],
        "stability": "stationary",
        "stale": False,
        "valid": True,
        "target_xy_m": None,
        "spatial_coordinates_used": False,
        "firmware": None,
        "notes": [
            f"scripted simulation case {case['case']}",
            "display bearing is not a measured radar angle",
            "breath, heart, distance, and target count are scripted stand-ins for the MR60BHA2 fields",
        ],
        "captured_at_utc": stamp,
        "source_mode": "simulation",
        "display_bearing_deg": case["bearing"],
        "case_name": case["case"],
    }


def _pose(state, point: dict, stamp: str) -> None:
    pose = {
        "x_cm": point["x_cm"],
        "y_cm": point["y_cm"],
        "heading_deg": 180,
        "source": "simulation_script",
        "valid": True,
        "error_cm": None,
        "captured_at_utc": stamp,
        "note": "Scripted simulation position, not a localization fix.",
    }
    state.pose = pose
    state.pose_trail.append(pose)


def _record_sensor_events(state, point: dict, stamp: str) -> None:
    point_id = str(point["id"])
    acoustic = state.acoustic or {}
    piezo = state.piezo or {}
    ultrasonic = state.ultrasonic or {}
    radar = state.radar or {}
    presence = "present" if radar.get("human_presence") else "no person"
    state.add_event(
        device="xvf3800",
        sensor="acoustic",
        summary=f"Scripted audio at {point_id}: class {acoustic.get('class')}. Synthetic sample, not a live microphone.",
        quality="synthetic",
        captured_at_utc=stamp,
        value=None,
        unit=None,
        site_id=point_id,
        acoustic_class=acoustic.get("class"),
    )
    state.add_event(
        device="piezo",
        sensor="piezo",
        summary=f"Scripted contact at {point_id}: peak {piezo.get('peak_adc_counts')} adc counts. Counts are not acceleration.",
        quality="synthetic",
        captured_at_utc=stamp,
        value=piezo.get("peak_adc_counts"),
        unit="adc_counts",
        site_id=point_id,
    )
    state.add_event(
        device="hc_sr04",
        sensor="ultrasonic",
        summary=f"Scripted ultrasonic at {point_id}: {ultrasonic.get('distance_cm')} cm.",
        quality="synthetic",
        captured_at_utc=stamp,
        value=ultrasonic.get("distance_cm"),
        unit="cm",
        site_id=point_id,
    )
    state.add_event(
        device="mr60bha2",
        sensor="radar",
        summary=(
            f"Scripted MR60BHA2 at {point_id}: {presence}"
            f", breath {radar.get('breath_rate_bpm')} breaths/min"
            f", heart {radar.get('heart_rate_bpm')} bpm"
            f", distance {radar.get('distance_m')} m. "
            "Breath, heart, and distance are scripted stand-ins. No measured angle."
        ),
        quality="synthetic",
        captured_at_utc=stamp,
        value=radar.get("distance_m"),
        unit="m",
        site_id=point_id,
    )


def _mark_devices(state, stamp: str) -> None:
    for device in state.devices:
        if device["device_id"] not in SIMULATED_DEVICES:
            continue
        device["state"] = "simulated"
        device["source_mode"] = "simulation"
        device["quality"] = "synthetic"
        device["last_seen_utc"] = stamp
        device["age_ms"] = 0
        device["error"] = "Scripted sample. The physical device is not open."


def _finish(state) -> None:
    state.run_active = False
    state.phase = "COMPLETE"
    state.scan_stage = "COMPLETE"
    state.run_elapsed_s = round(len(load_geometry()["measurement_points"]) * POINT_SECONDS, 1)
    from app.services.mission import request_reason
    from app.services.search_plan import plan_from_photo

    if state.search_plan is None:
        plan_from_photo()
    request_reason()
    state.add_event(
        device="simulation",
        sensor="script",
        summary="Simulation finished. Six scripted cases with sample image, audio, and sensor files.",
        quality="synthetic",
        captured_at_utc=utc_now(),
        value=None,
        unit=None,
    )
    _sync_trial(state)
    cancel_run()


def _tick(token: int) -> None:
    state = get_state()
    if token != _generation or not state.run_active:
        return
    elapsed = time.monotonic() - state.run_started
    state.run_elapsed_s = round(elapsed, 1)
    points = load_geometry()["measurement_points"]
    due = min(len(points), int(elapsed // POINT_SECONDS) + 1)
    while _index < due:
        _publish()
    if _index >= len(points) and elapsed >= len(points) * POINT_SECONDS:
        _finish(state)
        return
    _arm(1.0)


def _arm(delay: float) -> None:
    global _timer
    with _lock:
        token = _generation
        _timer = threading.Timer(delay, lambda: _tick(token))
        _timer.daemon = True
        _timer.start()
