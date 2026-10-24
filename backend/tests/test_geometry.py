from app.config.geometry import (
    center_separations,
    load_geometry,
    point_in_traversable,
    table_cm_to_display_px,
)


def test_plan_dimensions_and_separations() -> None:
    geometry = load_geometry()
    assert geometry["units"] == "cm"
    assert geometry["outer_cm"] == {"width": 105, "height": 80}
    assert geometry["inner_cm"]["width"] == 101
    assert geometry["inner_cm"]["height"] == 76
    assert geometry["sand"]["thick"]["cover_above_lids_cm"] == 10
    assert geometry["sand"]["thin"]["cover_above_lids_cm"] == 5
    assert geometry["drawing"]["pdf_in_repository"] is False

    separations = center_separations(geometry)
    documented = geometry["documented_nominal_separations_cm"]
    assert abs(separations["A_B"] - documented["A_B"]) < 0.15
    assert abs(separations["A_C"] - documented["A_C"]) < 0.15
    assert abs(separations["B_C"] - documented["B_C"]) < 0.05

    points = {point["id"]: point for point in geometry["measurement_points"]}
    assert points["A_FAR"]["y_cm"] - points["A_NEAR"]["y_cm"] == 25
    assert points["B_NEAR"]["y_cm"] - points["B_FAR"]["y_cm"] == 25


def test_display_conversion_keeps_y_down() -> None:
    assert table_cm_to_display_px(10, 20, 4) == (40, 80)
    assert point_in_traversable(52.5, 39.5)
    assert not point_in_traversable(1, 1)
