"""Synthetic envelopes for the six sand-table points.

These packets are not sensor readings. Measurements stay null.
"""

from datetime import datetime, timezone

POINTS = ("A_NEAR", "A_FAR", "B_NEAR", "B_FAR", "C_NEAR", "C_FAR")
KINDS = ("baseline", "ultrasonic", "audio", "radar")


def packets() -> list[dict]:
    stamped = datetime(2026, 10, 24, 20, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    rows = []
    sequence = 1
    for point_id in POINTS:
        for kind in KINDS:
            rows.append(
                {
                    "schema_version": "1.0",
                    "mode": "SIMULATION",
                    "synthetic": True,
                    "session_id": "mock-pi-session",
                    "sequence": sequence,
                    "timestamp_utc": stamped,
                    "test_point_id": point_id,
                    "kind": kind,
                    "position": {"source": "SCRIPTED", "valid": False},
                    "ultrasonic": {"distance_cm": None, "valid": False},
                    "audio": {"clip_id": None, "event": "UNKNOWN", "score": None},
                    "radar": {"presence": None, "distance_cm": None, "heart_rate_bpm": None, "breath_rate_bpm": None},
                    "model": {"state": "UNCONFIGURED", "advice": None},
                }
            )
            sequence += 1
    return rows


if __name__ == "__main__":
    import json

    for row in packets():
        print(json.dumps(row))
