from app.services.fusion import local_assessment, window_score
from app.services.heatmap import interpolate_markers, measured_points


def test_missing_modalities_are_unknown_not_zero() -> None:
    assert window_score(None, None, False) is None
    silence = window_score("silence", None, False)
    assert silence == 0.0
    knock = window_score("knock", 800, True)
    assert knock is not None and knock > 0.8
    partial = window_score(None, 800, False)
    assert partial == 0.8


def test_interpolation_is_labeled_and_not_in_the_measured_set() -> None:
    measured = [
        {"point_id": "A_FAR", "x_cm": 52.5, "y_cm": 39.5, "score": 0.9, "source_mode": "replay", "interpolated": False},
        {"point_id": "B_NEAR", "x_cm": 17.0, "y_cm": 65.5, "score": 0.1, "source_mode": "replay", "interpolated": False},
    ]
    synthetic = interpolate_markers(measured)
    assert synthetic and all(point["interpolated"] is True for point in synthetic)
    assert measured_points(measured + synthetic) == measured


def test_local_assessment_is_not_a_model() -> None:
    result = local_assessment(
        [{"event_id": "evt_0001", "acoustic_class": "knock", "site_id": "A_FAR"}],
        [],
    )
    assert result["provider"] == "deterministic_safety_fallback"
    assert result["nvidia_online"] is False
    assert result["recommendation"]["requires_approval"] is True
    assert result["recommendation"]["type"] == "needs_operator"
