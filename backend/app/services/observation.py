"""Immutable observation snapshots and schema checks for one assessment.

The model does not assign ids, timestamps, or evidence sufficiency.
Audio from the damaged microphone array is never stored as a zero or as a clear cell.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

SCHEMA_VERSION = 1
_CELL = re.compile(r"^r[1-3]c[1-3]$")
_SUFFICIENCY = {"insufficient", "limited", "supported"}
_CLAIMS = (
    "all clear",
    "survivor",
    "confirmed person",
    "person is present",
    "pulse",
    "heartbeat",
    "breathing",
    "no sound detected",
)
_SAFE_ACTIONS = {"inspect_cell", "continue_scan", "hold_for_operator", "none"}


def build_observation(state: Any) -> dict:
    """Copy the readings that may be shown or sent. Does not call hardware."""
    captures = list(getattr(state, "cell_captures", None) or [])
    readings: list[dict] = []
    cells: list[str] = []
    for point in captures:
        if not isinstance(point, dict):
            continue
        cell_id = str(point.get("point_id") or "")
        if not _CELL.match(cell_id):
            continue
        if cell_id not in cells:
            cells.append(cell_id)
        stored = point.get("readings") if isinstance(point.get("readings"), dict) else {}
        evidence = [item for item in point.get("evidence_event_ids") or [] if isinstance(item, str)]
        ultra = stored.get("ultrasonic_cm")
        if isinstance(ultra, (int, float)) and not isinstance(ultra, bool) and float(ultra) > 0:
            readings.append(
                {
                    "evidence_id": f"{cell_id}:ultrasonic",
                    "sensor": "hc_sr04",
                    "cell_id": cell_id,
                    "value": float(ultra),
                    "unit": "cm",
                    "quality": "measured",
                    "source_event_ids": evidence,
                }
            )
        distance = stored.get("distance_m")
        if isinstance(distance, (int, float)) and not isinstance(distance, bool) and float(distance) >= 0:
            readings.append(
                {
                    "evidence_id": f"{cell_id}:radar_range",
                    "sensor": "mr60bha2",
                    "cell_id": cell_id,
                    "value": float(distance),
                    "unit": "m",
                    "quality": "measured",
                    "source_event_ids": evidence,
                }
            )
        sound = stored.get("sound")
        if isinstance(sound, str) and sound.strip():
            readings.append(
                {
                    "evidence_id": f"{cell_id}:microphone",
                    "sensor": "xvf3800",
                    "cell_id": cell_id,
                    "value": sound,
                    "unit": "class",
                    "quality": "measured",
                    "source_event_ids": evidence,
                }
            )
        presence = stored.get("radar_presence")
        if isinstance(presence, bool):
            readings.append(
                {
                    "evidence_id": f"{cell_id}:radar_flag",
                    "sensor": "mr60bha2",
                    "cell_id": cell_id,
                    "value": presence,
                    "unit": "presence_flag",
                    "quality": "sensor_flag",
                    "source_event_ids": evidence,
                }
            )
    mode = str(getattr(state, "mode", "") or "")
    fixture = getattr(state, "fixture_name", None)
    origin = "replay" if mode in {"replay", "simulation"} or fixture else "live"
    pose = getattr(state, "pose", None) or {}
    cell = pose.get("cell_id") if isinstance(pose, dict) else None
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": f"snap_{uuid.uuid4().hex[:12]}",
        "session_id": str(getattr(state, "trial_id", None) or "live-session"),
        "origin": origin,
        "fixture": bool(fixture),
        "cell_id": cell if isinstance(cell, str) and _CELL.match(cell) else None,
        "pose_valid": bool(pose.get("valid")) if isinstance(pose, dict) else False,
        "cells": cells,
        "readings": readings,
        "audio": {"sensor": "xvf3800", "status": "available"},
        "excluded": [],
        "known_evidence_ids": [row["evidence_id"] for row in readings],
    }


def evidence_sufficiency(observation: dict) -> dict:
    """Compare stored non-acoustic readings. Missing audio is not a score."""
    readings = [row for row in observation.get("readings") or [] if isinstance(row, dict)]
    numeric = [
        row
        for row in readings
        if row.get("unit") in {"cm", "m"} and isinstance(row.get("value"), (int, float))
    ]
    cells = {str(row.get("cell_id")) for row in numeric}
    if not cells:
        return {
            "level": "insufficient",
            "reason": "No completed non-acoustic measurement is stored.",
            "comparable": False,
        }
    if len(cells) < 2 or not _values_differ(numeric):
        return {
            "level": "limited",
            "reason": "Stored readings do not distinguish one cell from another.",
            "comparable": False,
        }
    return {
        "level": "supported",
        "reason": "At least two cells have different measured ranges.",
        "comparable": True,
    }


def validate_assessment(payload: object, observation: dict) -> tuple[dict | None, str | None]:
    """Reject malformed model JSON. Does not run the text as a command."""
    if not isinstance(payload, dict):
        return None, "invalid_json_shape"
    summary = payload.get("summary")
    findings = payload.get("findings")
    action = payload.get("next_action")
    limitations = payload.get("limitations")
    if not isinstance(summary, str) or not summary.strip():
        return None, "invalid_summary"
    if _unsupported(summary):
        return None, "unsupported_claim"
    if not isinstance(findings, list):
        return None, "invalid_findings"
    known = set(observation.get("known_evidence_ids") or [])
    cells = set(observation.get("cells") or [])
    cleaned = []
    for finding in findings:
        if not isinstance(finding, dict):
            return None, "invalid_finding"
        text = finding.get("text")
        evidence_id = finding.get("evidence_id")
        cell_id = finding.get("cell_id")
        if not isinstance(text, str) or not text.strip() or _unsupported(text):
            return None, "unsupported_claim"
        if not isinstance(evidence_id, str) or evidence_id not in known:
            return None, "unknown_evidence_id"
        if cell_id is not None and (not isinstance(cell_id, str) or cell_id not in cells):
            return None, "unknown_cell_id"
        cleaned.append({"text": text.strip(), "evidence_id": evidence_id, "cell_id": cell_id})
    if not isinstance(limitations, list) or not all(isinstance(item, str) for item in limitations):
        return None, "invalid_limitations"
    if not isinstance(action, dict):
        return None, "invalid_action"
    kind = action.get("type")
    if kind not in _SAFE_ACTIONS:
        return None, "action_not_allowed"
    point = action.get("cell_id")
    if point is not None and (not isinstance(point, str) or point not in cells):
        return None, "unknown_cell_id"
    if any(_unsupported(item) for item in limitations):
        return None, "unsupported_claim"
    return {
        "summary": summary.strip(),
        "findings": cleaned,
        "limitations": limitations,
        "next_action": {"type": kind, "cell_id": point, "requires_operator": True},
    }, None


def stamp_assessment(
    body: dict | None,
    observation: dict,
    *,
    provider: str,
    model_id: str | None,
    latency_ms: float | None,
    live_call: bool,
    request_id: str,
) -> dict:
    """Server-owned ids. A local summary is never labeled as a cloud result."""
    sufficiency = evidence_sufficiency(observation)
    status = "completed" if body else "unavailable"
    summary = body["summary"] if body else "Assessment unavailable"
    return {
        "assessment_id": f"asm_{uuid.uuid4().hex[:12]}",
        "request_id": request_id,
        "snapshot_id": observation["snapshot_id"],
        "session_id": observation["session_id"],
        "status": status,
        "summary": summary,
        "findings": body["findings"] if body else [],
        "next_action": body["next_action"] if body else {"type": "hold_for_operator", "cell_id": None, "requires_operator": True},
        "limitations": body["limitations"] if body else [],
        "evidence_sufficiency": sufficiency["level"],
        "sufficiency_reason": sufficiency["reason"],
        "ranking_allowed": sufficiency["comparable"],
        "provider": provider,
        "model_id": model_id,
        "latency_ms": latency_ms,
        "live_call": live_call,
        "local_only": not live_call,
        "origin": observation["origin"],
        "fixture": observation["fixture"],
    }


def local_body(observation: dict) -> dict:
    sufficiency = evidence_sufficiency(observation)
    if sufficiency["comparable"]:
        action = {"type": "inspect_cell", "cell_id": _closest_cell(observation)}
        summary = "Stored range readings differ. Inspect the closest measured cell. This is a local summary, not a cloud-model result."
    else:
        action = {"type": "hold_for_operator", "cell_id": None}
        summary = "No completed observations distinguish a next cell. This is a local summary, not a cloud-model result."
    return {
        "summary": summary,
        "findings": [
            {
                "text": row["evidence_id"],
                "evidence_id": row["evidence_id"],
                "cell_id": row["cell_id"],
            }
            for row in observation.get("readings") or []
            if row.get("unit") in {"cm", "m"}
        ][:8],
        "limitations": [
            "Deterministic local summary.",
            "The microphone reading is the reported sound category.",
        ],
        "next_action": action,
    }


def attach_to_reasoning(state: Any, result: dict) -> dict:
    """Add server-owned snapshot identity. Does not replace a validated summary."""
    observation = build_observation(state)
    state.observation = observation
    sufficiency = evidence_sufficiency(observation)
    result["snapshot_id"] = observation["snapshot_id"]
    result["session_id"] = observation["session_id"]
    result["evidence_sufficiency"] = sufficiency["level"]
    result["sufficiency_reason"] = sufficiency["reason"]
    result["ranking_allowed"] = sufficiency["comparable"]
    result["audio_note"] = "The microphone is available. Its reading is the reported sound."
    if not result.get("live_call"):
        result["local_only"] = True
    return result


def accept_result(result_session: str, result_request: str, session_id: str, request_id: str) -> bool:
    """A late reply from an older session or request must not replace the current assessment."""
    return result_session == session_id and result_request == request_id


def _values_differ(rows: list[dict]) -> bool:
    by_sensor: dict[str, set[float]] = {}
    for row in rows:
        by_sensor.setdefault(str(row.get("sensor")), set()).add(round(float(row["value"]), 2))
    return any(len(values) > 1 for values in by_sensor.values())


def _closest_cell(observation: dict) -> str | None:
    best: tuple[float, str] | None = None
    for row in observation.get("readings") or []:
        if row.get("unit") != "cm":
            continue
        value = float(row["value"])
        cell = str(row["cell_id"])
        if best is None or value < best[0]:
            best = (value, cell)
    return best[1] if best else None


def _unsupported(text: str) -> bool:
    folded = text.lower()
    return any(claim in folded for claim in _CLAIMS)
