import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "mock_pi"))

from mock_raspberry_pi import POINTS, packets  # noqa: E402


def test_mock_packets_cover_six_points_without_fake_readings() -> None:
    rows = packets()
    assert len(rows) == 24
    assert {row["test_point_id"] for row in rows} == set(POINTS)
    for row in rows:
        assert row["mode"] == "SIMULATION"
        assert row["synthetic"] is True
        assert row["ultrasonic"]["distance_cm"] is None
        assert row["audio"]["score"] is None
        assert row["radar"]["heart_rate_bpm"] is None
        assert row["position"]["valid"] is False
        assert row["model"]["state"] == "UNCONFIGURED"
