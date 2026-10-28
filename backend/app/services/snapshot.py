from app.ai.nebius_client import ai_status
from app.config.geometry import load_geometry
from app.drivers.camera_pi import streaming_count
from app.services.clock import utc_now
from app.state import LIMITATIONS, AppState

LIVE_BADGE_REQUIRES = ("mr60bha2", "hc_sr04", "xvf3800", "camera_top")


def _rover_leg(state: AppState) -> dict | None:
    from app.services.rover_track import public_leg

    return public_leg(state)


def build_snapshot(state: AppState) -> dict:
    ai = ai_status()
    nvidia_online = bool(
        state.reasoning
        and state.reasoning.get("provider") == "nebius_token_factory"
        and state.reasoning.get("live_call")
        and state.reasoning.get("nvidia_online")
    )
    devices = [_public_device(device, ai, nvidia_online) for device in state.devices]
    badge = _badge(state)
    return {
        "version": "1",
        "badge": badge,
        "mode": state.mode,
        "system_live": _system_live(state, devices),
        "mission_phase": state.phase,
        "safety_state": state.safety,
        "run_active": state.run_active,
        "scan_stage": state.scan_stage,
        "run_elapsed_s": state.run_elapsed_s,
        "nvidia_online": nvidia_online,
        "ai": ai,
        "devices": devices,
        "cameras": state.cameras,
        "streaming_camera_count": streaming_count(state.cameras),
        "camera_count": len(state.cameras),
        "radar": state.radar,
        "ultrasonic": state.ultrasonic,
        "acoustic": state.acoustic,
        "impulse": state.impulse,
        "piezo": state.piezo,
        "pose": state.pose,
        "pose_trail": state.pose_trail,
        "rover_leg": _rover_leg(state),
        "solenoid": state.solenoid.public_status(),
        "heatmap_points": state.heatmap,
        "scan_route": [
            {
                "id": cell["id"],
                "x_cm": cell["x_cm"],
                "y_cm": cell["y_cm"],
                "blocked": bool(cell.get("blocked")),
                "heading_deg": cell.get("heading_deg"),
                "border_cm": cell.get("border_cm"),
                "site_id": cell.get("site_id"),
            }
            for cell in (state.scan_route or [])
        ],
        "blocked_cells": list(state.blocked_cells),
        "events": list(reversed(state.events[-40:])),
        "reasoning": state.reasoning,
        "search_plan": state.search_plan,
        "scene_note": state.scene_note,
        "ai_usage": state.ai_usage,
        "geometry_revision": load_geometry()["geometry_revision"],
        "limitations": list(LIMITATIONS),
        "updated_at_utc": utc_now(),
        "calibration": state.calibration,
        "acoustic_envelope_dbfs": state.acoustic_envelope,
        "acoustic_waveform": state.acoustic_waveform,
        "piezo_waveform": state.piezo_waveform,
        "rover_trace": state.rover_trace,
        "acoustic_envelope_note": (
            "Envelope uses dBFS. Exact digital zeros are drawn at -80 dBFS. This is not dB SPL."
        ),
        "impulse_envelope_dbfs": state.impulse_envelope,
        "operator_output_locked": True,
        "trial_id": state.trial_id,
        "fixture_name": state.fixture_name,
        "malformed_radar_lines": state.malformed_radar,
        "sensor_gates": _sensor_gates(),
        "remote": _remote_state(),
        "legacy_simulation_active": state.legacy_active,
    }


def _public_device(device: dict, ai: dict, nvidia_online: bool) -> dict:
    item = dict(device)
    if item["device_id"] != "nebius_nvidia":
        return item
    item["quality"] = ai["status"]
    item["error"] = ai["message"]
    item["firmware"] = None
    if nvidia_online:
        item["state"] = "connected"
        item["source_mode"] = "live"
        return item
    item["state"] = "disconnected"
    item["source_mode"] = "unavailable"
    return item


def _sensor_gates() -> dict:
    from app.services.sensor_gates import public_gates

    return public_gates()


def _remote_state() -> dict:
    from app.services.remote_drive import public_remote

    return public_remote()


def _badge(state: AppState) -> str:
    if state.mode == "live":
        return "LIVE"
    if state.mode == "replay":
        return "REPLAY"
    if state.mode == "manual":
        return "MANUAL"
    if state.mode == "simulation" or state.legacy_active:
        return "SIMULATION"
    return "DISCONNECTED"


def _system_live(state: AppState, devices: list[dict]) -> bool:
    if state.mode != "live":
        return False
    by_id = {device["device_id"]: device for device in devices}
    return all(
        by_id[name]["state"] == "connected" and by_id[name]["source_mode"] == "live"
        for name in LIVE_BADGE_REQUIRES
    )
