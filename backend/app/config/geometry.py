import json
import math
from functools import lru_cache

from app.paths import GEOMETRY_PATH


@lru_cache(maxsize=1)
def load_geometry() -> dict:
    data = json.loads(GEOMETRY_PATH.read_text(encoding="utf-8"))
    _validate(data)
    return data


def _validate(data: dict) -> None:
    if data.get("units") != "cm":
        raise ValueError("sand-table geometry must use centimeters")
    outer = data["outer_cm"]
    inner = data["inner_cm"]
    derived_x = (outer["width"] - inner["width"]) / 2
    derived_y = (outer["height"] - inner["height"]) / 2
    if abs(derived_x - inner["origin_x_cm"]) > 1e-6:
        raise ValueError("inner x origin does not match the outer and inner widths")
    if abs(derived_y - inner["origin_y_cm"]) > 1e-6:
        raise ValueError("inner y origin does not match the outer and inner heights")
    identifiers = [point["id"] for point in data["measurement_points"]]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("measurement point ids must be unique")


def point_map(data: dict | None = None) -> dict[str, dict]:
    geometry = data or load_geometry()
    return {point["id"]: point for point in geometry["measurement_points"]}


def known_point_ids(data: dict | None = None) -> set[str]:
    return set(point_map(data))


def separation_cm(first: dict, second: dict) -> float:
    return math.hypot(first["x_cm"] - second["x_cm"], first["y_cm"] - second["y_cm"])


def center_separations(data: dict | None = None) -> dict[str, float]:
    points = point_map(data)
    return {
        "A_B": separation_cm(points["A_NEAR"], points["B_NEAR"]),
        "A_C": separation_cm(points["A_NEAR"], points["C_NEAR"]),
        "B_C": separation_cm(points["B_NEAR"], points["C_NEAR"]),
    }


def table_cm_to_display_px(
    x_cm: float, y_cm: float, px_per_cm: float
) -> tuple[float, float]:
    """Map table centimeters to a display whose +Y axis points down, matching the plan."""
    return (x_cm * px_per_cm, y_cm * px_per_cm)


def traversable_bounds(data: dict | None = None) -> dict[str, float]:
    geometry = data or load_geometry()
    inner = geometry["inner_cm"]
    inset = geometry["safety_defaults"]["unmeasured_footprint_inset_cm"]
    return {
        "min_x": inner["origin_x_cm"] + inset,
        "min_y": inner["origin_y_cm"] + inset,
        "max_x": inner["origin_x_cm"] + inner["width"] - inset,
        "max_y": inner["origin_y_cm"] + inner["height"] - inset,
    }


def point_in_traversable(x_cm: float, y_cm: float, data: dict | None = None) -> bool:
    bounds = traversable_bounds(data)
    return (
        bounds["min_x"] <= x_cm <= bounds["max_x"]
        and bounds["min_y"] <= y_cm <= bounds["max_y"]
    )
