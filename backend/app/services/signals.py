"""Traces and obstacle reaction shared by the simulation and a plugged-in sensor."""

from __future__ import annotations

import math

from app.config.geometry import load_geometry
from app.config.settings import ULTRASONIC_STOP_CM
from app.services.clock import utc_now


def contact_waveform(peak: float, count: int = 128) -> list[float]:
    """Ring-down in ADC counts. The peak of the trace is the reported peak."""
    peak = abs(float(peak))
    if count <= 0:
        return []
    if peak <= 0:
        return [0.0] * count
    sharp = peak >= 200
    decay = 140.0 if sharp else 36.0
    tone = 280.0 if sharp else 55.0
    raw: list[float] = []
    for index in range(count):
        t = index / 1000.0
        ring = math.exp(-t * decay) * math.sin(2.0 * math.pi * tone * t)
        floor = 0.05 * math.sin(2.0 * math.pi * 28.0 * t + index * 0.17)
        raw.append(ring + floor)
    scale = max(abs(value) for value in raw) or 1.0
    return [round(value / scale * peak, 2) for value in raw]


def wrap_deg(delta: float) -> float:
    while delta > 180.0:
        delta -= 360.0
    while delta < -180.0:
        delta += 360.0
    return delta


def encoder_step(heading_delta_deg: float) -> tuple[float, float]:
    """Wheel ticks for one cell. A left turn slows the left wheel."""
    turn = max(-1.0, min(1.0, wrap_deg(heading_delta_deg) / 90.0))
    return round(8.0 * (1.0 - turn), 2), round(8.0 * (1.0 + turn), 2)


def append_ticks(state, left: float, right: float, source_mode: str, note: str) -> None:
    prior = state.rover_trace or {}
    left_series = [float(value) for value in prior.get("left") or []]
    right_series = [float(value) for value in prior.get("right") or []]
    left_series.append(float(left))
    right_series.append(float(right))
    left_series = left_series[-48:]
    right_series = right_series[-48:]
    state.rover_trace = {
        "left": [round(value, 2) for value in left_series],
        "right": [round(value, 2) for value in right_series],
        "left_counts": round(sum(left_series), 1),
        "right_counts": round(sum(right_series), 1),
        "unit": "ticks",
        "source_mode": source_mode,
        "note": note,
        "phase": state.phase,
    }


def place_echo(state) -> None:
    sample = state.ultrasonic
    pose = state.pose or {}
    if not sample:
        return
    distance = sample.get("distance_cm")
    x_cm = pose.get("x_cm")
    y_cm = pose.get("y_cm")
    heading = pose.get("heading_deg")
    if (
        isinstance(distance, bool)
        or not isinstance(distance, (int, float))
        or x_cm is None
        or y_cm is None
        or heading is None
    ):
        sample["echo_x_cm"] = None
        sample["echo_y_cm"] = None
        return
    radians = math.radians(float(heading))
    raw_x = float(x_cm) + float(distance) * math.cos(radians)
    raw_y = float(y_cm) + float(distance) * math.sin(radians)
    outer = load_geometry()["outer_cm"]
    sample["echo_x_cm"] = round(min(max(0.0, raw_x), float(outer["width"])), 1)
    sample["echo_y_cm"] = round(min(max(0.0, raw_y), float(outer["height"])), 1)


def facing_deg(route: list[dict], cursor: int, here: dict, fallback: float) -> float:
    for item in route[cursor:]:
        if item.get("blocked"):
            continue
        return math.degrees(math.atan2(item["y_cm"] - here["y_cm"], item["x_cm"] - here["x_cm"]))
    return fallback


def react_to_range(state, cursor: int) -> str | None:
    """A return inside 20 cm blocks the next grid cell and holds the rover in listen.

    Named sites stay on the route. The same rule runs for a scripted sample and a live line.
    """
    sample = state.ultrasonic or {}
    distance = sample.get("distance_cm")
    timeout = bool(sample.get("echo_timeout"))
    close = timeout or (
        isinstance(distance, (int, float)) and not isinstance(distance, bool) and float(distance) < ULTRASONIC_STOP_CM
    )
    if not close:
        if state.phase == "LISTEN":
            state.phase = "SCANNING"
        if state.rover_trace is not None:
            state.rover_trace["note"] = "Rolling. Range is outside the 20 cm stop."
            state.rover_trace["phase"] = state.phase
        return None

    blocked: str | None = None
    for item in (state.scan_route or [])[cursor:]:
        if item.get("blocked"):
            continue
        if str(item["id"]).startswith("x"):
            item["blocked"] = True
            blocked = str(item["id"])
            if blocked not in state.blocked_cells:
                state.blocked_cells.append(blocked)
        break
    state.phase = "LISTEN"
    shown = distance if isinstance(distance, (int, float)) and not isinstance(distance, bool) else "timeout"
    if blocked:
        note = f"Ultrasonic {shown} cm blocked {blocked}. Rover rerouted and is listening."
    else:
        note = f"Ultrasonic {shown} cm is inside the stop margin. Rover is listening. The named cell stays on the route."
    if state.rover_trace is not None:
        state.rover_trace["note"] = note
        state.rover_trace["phase"] = "LISTEN"
    state.add_event(
        device="hc_sr04",
        sensor="ultrasonic",
        summary=note,
        quality=sample.get("quality") or "sensor",
        captured_at_utc=utc_now(),
        value=distance if isinstance(distance, (int, float)) and not isinstance(distance, bool) else None,
        unit="cm",
        site_id=blocked,
    )
    return blocked
