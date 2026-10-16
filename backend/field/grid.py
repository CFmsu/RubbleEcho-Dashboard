"""4×4 inspection grid over a photograph.

Columns A–D run left to right. Rows 1–4 run top to bottom.
A1 is the top-left cell. D4 is the bottom-right cell.
The grid covers the full image. It is not a crop.
"""

from __future__ import annotations

CELL_COLUMNS = "ABCD"
CELL_ROWS = (1, 2, 3, 4)
CELL_IDS: tuple[str, ...] = tuple(f"{column}{row}" for row in CELL_ROWS for column in CELL_COLUMNS)


def cell_at(x_norm: float, y_norm: float) -> str:
    """Map a point in the image to a cell.

    x_norm and y_norm are fractions of the image width and height, origin at the top left.
    Values of 1.0 stay inside D and row 4.
    """
    if not 0.0 <= x_norm <= 1.0 or not 0.0 <= y_norm <= 1.0:
        raise ValueError("normalized coordinates must be inside 0..1")
    column = min(3, int(x_norm * 4))
    row = min(3, int(y_norm * 4))
    return f"{CELL_COLUMNS[column]}{row + 1}"


def cell_bounds(cell: str) -> dict[str, float]:
    """Return the cell rectangle as fractions of the image: left, top, right, bottom."""
    normalized = cell.strip().upper()
    if normalized not in CELL_IDS:
        raise ValueError(f"unknown cell {cell}")
    column = CELL_COLUMNS.index(normalized[0])
    row = int(normalized[1]) - 1
    return {
        "left": column / 4,
        "top": row / 4,
        "right": (column + 1) / 4,
        "bottom": (row + 1) / 4,
    }
