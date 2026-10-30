"""Choose the next square when the front sweep sees an obstacle.

The nine squares stay the visit list. A blocked edge is not driven. The next
command is one step toward the earliest remaining square that can still be
reached, so a detour may cross a square that was already visited. Every square
is still held the first time the rover arrives.
"""

from __future__ import annotations

from app.config.settings import ULTRASONIC_STOP_CM

PREF = (
    "r1c1",
    "r1c2",
    "r1c3",
    "r2c3",
    "r2c2",
    "r2c1",
    "r3c1",
    "r3c2",
    "r3c3",
)
# drow, dcol, heading. Row increases south. Heading 0 faces east.
_DIRS = ((0, 1, 0), (1, 0, 90), (0, -1, 180), (-1, 0, 270))

_visited: set[str] = set()
_blocked: set[frozenset[str]] = set()
_heading = 0
_current = "r1c1"
_sweep_open = False
_sweep_cell: str | None = None
_sweep_heading = 0
chosen: str | None = None


def reset_route() -> None:
    global _heading, _current, chosen, _sweep_open, _sweep_cell, _sweep_heading
    _visited.clear()
    _blocked.clear()
    _heading = 0
    _current = "r1c1"
    _sweep_open = False
    _sweep_cell = None
    _sweep_heading = 0
    chosen = None


def open_sweep(cell: str, heading: int) -> None:
    """The rover is stopped and the Pi may sweep this square."""
    global _current, _heading, _sweep_open, _sweep_cell, _sweep_heading
    _current = cell
    _heading = int(heading) % 360
    _visited.add(cell)
    _sweep_cell = cell
    _sweep_heading = _heading
    _sweep_open = True


def sweep_status() -> dict:
    return {"ready": _sweep_open, "cell": _sweep_cell, "heading": _sweep_heading}


def accept_beams(beams: list[dict]) -> dict:
    """Store the Pi sweep and choose the next adjacent square."""
    global _sweep_open, chosen
    if not _sweep_open or not _sweep_cell:
        return {"ok": False}
    cell = _sweep_cell
    heading = _sweep_heading
    _sweep_open = False
    _apply_beams(cell, heading, beams)
    chosen = first_step(_current, _visited, _blocked)
    return {"ok": True, "cell": cell, "heading": heading, "next": chosen}


def note_moving(origin: str, dest: str) -> None:
    global _heading, _current
    face = _face(origin, dest)
    if face is not None:
        _heading = face
    _current = origin


def note_scan(cell: str, heading: int, beams: list[dict]) -> str | None:
    """Record this stop and return the next adjacent square, if one remains."""
    global _heading, _current, chosen
    _current = cell
    _heading = int(heading) % 360
    _visited.add(cell)
    _apply_beams(cell, _heading, beams)
    chosen = first_step(_current, _visited, _blocked)
    return chosen


def note_transit(cell: str) -> str | None:
    """A square already held. Keep going toward the rest of the grid."""
    global _current, _heading, chosen
    face = _face(_current, cell)
    if face is not None:
        _heading = face
    _current = cell
    chosen = first_step(_current, _visited, _blocked)
    return chosen


def first_step(current: str, visited: set[str], blocked: set[frozenset[str]]) -> str | None:
    targets = [cell for cell in PREF if cell not in visited]
    if not targets:
        return None
    parent: dict[str, str | None] = {current: None}
    waiting = [current]
    while waiting:
        here = waiting.pop(0)
        for nxt in _open_neighbors(here, blocked):
            if nxt in parent:
                continue
            parent[nxt] = here
            waiting.append(nxt)
    for target in targets:
        if target not in parent:
            continue
        step = target
        while parent[step] not in {current, None}:
            step = parent[step]  # type: ignore[index]
        if parent[step] == current:
            return step
    return None


def _apply_beams(cell: str, heading: int, beams: list[dict]) -> None:
    nearest = {"left": None, "forward": None, "right": None}
    for beam in beams:
        try:
            deg = int(beam.get("deg"))
            cm = float(beam.get("cm"))
        except (TypeError, ValueError):
            continue
        side = _sector(deg)
        if side is None or cm <= 0:
            continue
        previous = nearest[side]
        if previous is None or cm < previous:
            nearest[side] = cm
    faces = {
        "forward": heading % 360,
        "left": (heading - 90) % 360,
        "right": (heading + 90) % 360,
    }
    for side, face in faces.items():
        distance = nearest[side]
        if distance is None or distance >= ULTRASONIC_STOP_CM:
            continue
        other = _neighbor_on(cell, face)
        if other is not None:
            _blocked.add(frozenset((cell, other)))


def _sector(deg: int) -> str | None:
    # Servo 90 looks forward, 0 looks left, and 180 looks right.
    if deg < 70:
        return "left"
    if deg > 110:
        return "right"
    return "forward"


def _neighbor_on(cell: str, heading: int) -> str | None:
    parsed = _parse(cell)
    if parsed is None:
        return None
    row, col = parsed
    for drow, dcol, face in _DIRS:
        if face != heading % 360:
            continue
        nrow, ncol = row + drow, col + dcol
        if 0 <= nrow < 3 and 0 <= ncol < 3:
            return _name(nrow, ncol)
    return None


def _open_neighbors(cell: str, blocked: set[frozenset[str]]) -> list[str]:
    found = []
    for _drow, _dcol, face in _DIRS:
        other = _neighbor_on(cell, face)
        if other is None:
            continue
        if frozenset((cell, other)) in blocked:
            continue
        found.append(other)
    return found


def _face(origin: str, dest: str) -> int | None:
    start = _parse(origin)
    end = _parse(dest)
    if start is None or end is None:
        return None
    row, col = start
    drow, dcol = end
    drow -= row
    dcol -= col
    for step_row, step_col, face in _DIRS:
        if step_row == drow and step_col == dcol:
            return face
    return None


def _parse(cell: str) -> tuple[int, int] | None:
    if len(cell) != 4 or cell[0] != "r" or cell[2] != "c":
        return None
    if cell[1] not in "123" or cell[3] not in "123":
        return None
    return int(cell[1]) - 1, int(cell[3]) - 1


def _name(row: int, col: int) -> str:
    return f"r{row + 1}c{col + 1}"
