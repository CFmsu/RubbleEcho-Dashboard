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


def search_lattice(data: dict | None = None) -> list[dict]:
    """Three by three cells covering the inner rectangle.

    Even rows run left to right and odd rows run right to left. Heading follows
    the row, and border_cm is the clearance to that side of the table. The last
    cell of a row is the short reading that turns the route the other way.
    """
    geometry = data or load_geometry()
    inner = geometry["inner_cm"]
    origin_x = float(inner["origin_x_cm"])
    origin_y = float(inner["origin_y_cm"])
    cell_w = float(inner["width"]) / 3.0
    cell_h = float(inner["height"]) / 3.0
    left = origin_x
    right = origin_x + float(inner["width"])
    cells: list[dict] = []
    for row in range(3):
        columns = range(3) if row % 2 == 0 else range(2, -1, -1)
        heading = 0.0 if row % 2 == 0 else 180.0
        for col in columns:
            x_cm = round(origin_x + (col + 0.5) * cell_w, 1)
            y_cm = round(origin_y + (row + 0.5) * cell_h, 1)
            border = round((right - x_cm) if heading == 0.0 else (x_cm - left), 1)
            cells.append(
                {
                    "id": f"r{row + 1}c{col + 1}",
                    "x_cm": x_cm,
                    "y_cm": y_cm,
                    "row": row,
                    "col": col,
                    "heading_deg": heading,
                    "border_cm": border,
                    "site_id": _site_in_cell(geometry["measurement_points"], origin_x, origin_y, cell_w, cell_h, row, col),
                }
            )
    return cells


def _site_in_cell(points: list[dict], origin_x: float, origin_y: float, cell_w: float, cell_h: float, row: int, col: int) -> str | None:
    for point in points:
        point_col = math.floor((float(point["x_cm"]) - origin_x) / cell_w)
        point_row = math.floor((float(point["y_cm"]) - origin_y) / cell_h)
        if point_row == row and point_col == col:
            return str(point["id"])
    return None
