import json

from app.config.geometry import point_map
from app.config.settings import SYNC_TOLERANCE_MS
from app.drivers.piezo import piezo_features
from app.drivers.radar_mr60bha2 import parse_radar_line
from app.drivers.ultrasonic import parse_ultrasonic
from app.paths import SAMPLE_FIXTURE
from app.services.clock import fixture_time
from app.services.feature_extraction import classify_window, envelope_dbfs
from app.services.fusion import fuse_sites, window_score
from app.state import AppState


def load_replay(state: AppState, fixture_name: str = "sample_trial") -> None:
    if fixture_name != "sample_trial":
        raise FileNotFoundError(fixture_name)
    rows = []
    for line in (SAMPLE_FIXTURE / "events.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))

    state.mode = "replay"
    state.fixture_name = fixture_name
    state.phase = "DEVICE_CHECK"
    points = point_map()
    audio_records: list[dict] = []
    piezo_records: list[dict] = []

    state.add_event(
        device="mission",
        sensor="mission",
        summary="Replay fixture loaded. Values are not live sensor readings.",
        quality="replay_fixture",
        captured_at_utc=fixture_time(0),
        value=None,
        unit=None,
    )

    for row in rows:
        kind = row["kind"]
        at_ms = int(row["at_ms"])
        stamp = fixture_time(at_ms)
        if kind == "radar_line":
            observation, error = parse_radar_line(row["line"])
            if error or observation is None:
                state.malformed_radar += 1
                state.add_event(
                    device="mr60bha2",
                    sensor="radar",
                    summary="Malformed radar line ignored.",
                    quality="error",
                    captured_at_utc=stamp,
                    value=None,
                    unit=None,
                )
                continue
            observation["source_mode"] = "replay"
            observation["captured_at_utc"] = observation.get("captured_at_utc") or stamp
            state.radar = observation
            state.mark_replay_device("mr60bha2", stamp)
            presence = observation["human_presence"]
            state.add_event(
                device="mr60bha2",
                sensor="radar",
                summary=f"Radar presence {presence!s}. Spatial target not used.",
                quality="replay_fixture",
                captured_at_utc=stamp,
                value=presence,
                unit="bool_or_null",
                site_id=None,
            )
        elif kind == "ultrasonic":
            parsed = parse_ultrasonic(row)
            parsed["source_mode"] = "replay"
            state.ultrasonic = parsed
            state.mark_replay_device("hc_sr04", stamp)
            state.samples.append(
                {
                    "captured_at_utc": stamp,
                    "sensor": "hc_sr04",
                    "quantity": "obstacle_distance",
                    "value": parsed["distance_cm"],
                    "unit": "cm",
                    "quality": parsed["quality"],
                    "mode": "replay",
                    "x_cm": None,
                    "y_cm": None,
                }
            )
            distance = parsed["distance_cm"]
            summary = (
                "Ultrasonic echo timeout. Path is not clear."
                if parsed["echo_timeout"]
                else f"Obstacle distance {distance} cm."
            )
            state.add_event(
                device="hc_sr04",
                sensor="ultrasonic",
                summary=summary,
                quality=parsed["quality"],
                captured_at_utc=stamp,
                value=distance,
                unit="cm",
            )
        elif kind == "audio_window":
            context = {
                "site_id": row.get("site_id"),
                "source_mode": "replay",
                "motors_running": bool(row.get("motors_running", False)),
                "solenoid_commanded": bool(row.get("solenoid_commanded", False)),
            }
            acoustic = classify_window(
                row["samples"], row["sample_rate_hz"], stamp, context
            )
            envelope = envelope_dbfs(row["samples"])
            event = state.add_event(
                device="xvf3800",
                sensor="acoustic",
                summary=f"{acoustic['class']} at {row.get('site_id')}",
                quality="replay_fixture",
                captured_at_utc=stamp,
                value=acoustic["model_score"],
                unit="uncalibrated_raw_score" if acoustic["model_score"] is not None else "class",
                site_id=row.get("site_id"),
                acoustic_class=acoustic["class"],
            )
            state.acoustic = {**acoustic, "event_id": event["event_id"]}
            state.acoustic_envelope = envelope
            state.mark_replay_device("xvf3800", stamp)
            if acoustic["class"] == "knock":
                state.impulse = state.acoustic
                state.impulse_envelope = envelope
            audio_records.append(
                {
                    "at_ms": at_ms,
                    "site_id": row.get("site_id"),
                    "event_id": event["event_id"],
                    "acoustic_class": acoustic["class"],
                    "envelope": envelope,
                }
            )
        elif kind == "piezo":
            features = piezo_features(
                row["samples"],
                row["sample_rate_hz"],
                row.get("contact_state", "stationary_contact_sensor"),
                row.get("site_id"),
                bool(row.get("clipped", False)),
            )
            features["source_mode"] = "replay"
            event = state.add_event(
                device="piezo",
                sensor="piezo",
                summary=f"Piezo peak {features['peak_adc_counts']} adc counts at {row.get('site_id')}",
                quality="replay_fixture",
                captured_at_utc=stamp,
                value=features["peak_adc_counts"],
                unit="adc_counts",
                site_id=row.get("site_id"),
            )
            state.mark_replay_device("piezo", stamp)
            piezo_records.append(
                {
                    "at_ms": at_ms,
                    "site_id": row.get("site_id"),
                    "event_id": event["event_id"],
                    "peak": features["peak_adc_counts"],
                    "features": features,
                }
            )
            state.piezo = features
        elif kind == "pose":
            point = points.get(row.get("point_id"))
            pose = {
                "x_cm": row.get("x_cm", point["x_cm"] if point else None),
                "y_cm": row.get("y_cm", point["y_cm"] if point else None),
                "heading_deg": row.get("heading_deg"),
                "source": "replay_script",
                "calibration_id": None,
                "valid": bool(row.get("valid", False)),
                "error_cm": row.get("error_cm"),
                "captured_at_utc": stamp,
                "note": "Scripted replay position, not a live localization fix.",
            }
            state.pose = pose
            state.pose_trail.append(pose)
            state.add_event(
                device="pose",
                sensor="pose",
                summary="Replay script position recorded.",
                quality="replay_script",
                captured_at_utc=stamp,
                value=pose["x_cm"],
                unit="cm",
                site_id=row.get("point_id"),
            )
        elif kind == "solenoid_request":
            result = state.solenoid.request_pulse(
                int(row.get("width_ms", 40)),
                bool(row.get("rover_moving", False)),
                at_ms,
                bool(row.get("consent", False)),
            )
            state.add_event(
                device="solenoid",
                sensor="solenoid",
                summary=f"Knock request {result['reason']}. Output stayed off.",
                quality="output_locked",
                captured_at_utc=stamp,
                value=row.get("width_ms"),
                unit="ms",
            )

    used_piezo: set[int] = set()
    windows = []
    for audio in audio_records:
        match_index = _closest_piezo(audio, piezo_records, used_piezo)
        peak = None
        coincident = False
        evidence = [audio["event_id"]]
        if match_index is not None:
            used_piezo.add(match_index)
            peak = piezo_records[match_index]["peak"]
            coincident = audio["acoustic_class"] == "knock"
            evidence.append(piezo_records[match_index]["event_id"])
            if state.piezo and state.piezo.get("site_id") == audio["site_id"]:
                state.piezo["correlated_knock_id"] = (
                    audio["event_id"] if coincident else state.piezo.get("correlated_knock_id")
                )
        point = points.get(audio["site_id"], {})
        windows.append(
            {
                "site_id": audio["site_id"],
                "x_cm": point.get("x_cm"),
                "y_cm": point.get("y_cm"),
                "score": window_score(audio["acoustic_class"], peak, coincident),
                "event_id": audio["event_id"],
                "acoustic_class": audio["acoustic_class"],
                "piezo_peak": peak,
                "source_mode": "replay",
                "evidence_event_ids": evidence,
            }
        )
    for index, piezo in enumerate(piezo_records):
        if index in used_piezo:
            continue
        point = points.get(piezo["site_id"], {})
        windows.append(
            {
                "site_id": piezo["site_id"],
                "x_cm": point.get("x_cm"),
                "y_cm": point.get("y_cm"),
                "score": window_score(None, piezo["peak"], False),
                "event_id": piezo["event_id"],
                "acoustic_class": None,
                "piezo_peak": piezo["peak"],
                "source_mode": "replay",
            }
        )

    state.heatmap = fuse_sites(windows)
    for phase in ("CALIBRATE", "SURVEY", "PASSIVE_LISTEN", "FUSE"):
        state.phase = phase
        state.add_event(
            device="mission",
            sensor="mission",
            summary=f"Software phase {phase}. No motor command was sent.",
            quality="software",
            captured_at_utc=fixture_time(0),
            value=None,
            unit=None,
        )
    state.phase = "COMPLETE"
    state.safety = "HOLD"


def _closest_piezo(audio: dict, piezos: list[dict], used: set[int]) -> int | None:
    best = None
    best_gap = SYNC_TOLERANCE_MS + 1
    for index, piezo in enumerate(piezos):
        if index in used or piezo["site_id"] != audio["site_id"]:
            continue
        gap = abs(piezo["at_ms"] - audio["at_ms"])
        if gap <= SYNC_TOLERANCE_MS and gap < best_gap:
            best = index
            best_gap = gap
    return best
