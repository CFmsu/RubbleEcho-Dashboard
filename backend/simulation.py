import random
from dataclasses import dataclass, field
from math import hypot
from time import monotonic
from typing import Literal

ScenarioId = Literal["earthquake", "flood", "collapse"]
MissionStatus = Literal["STANDBY", "ACTIVE", "PAUSED", "DONE"]
MissionPhase = Literal["explore", "knock", "listen", "decide"]

GRID_WIDTH = 12
GRID_HEIGHT = 12
TICK_SECONDS = 0.5
# Fixed demo geometry makes every presentation run reproducible.
DEMO_PROBE_PATH = ((1, 1), (3, 3), (5, 5), (7, 7), (9, 9))
DEMO_SOURCE = (10, 10)
SEARCH_PATH = (
    (1, 1), (3, 4), (6, 2), (9, 3), (10, 7), (7, 9),
    (4, 10), (2, 7), (5, 5), (8, 5), (10, 10), (1, 10),
)

SCENARIOS = [
    {
        "id": "earthquake",
        "label": "Earthquake",
        "width": GRID_WIDTH,
        "height": GRID_HEIGHT,
        "description": "Search rooms and corridors after a strong quake.",
    },
    {
        "id": "flood",
        "label": "Flood",
        "width": GRID_WIDTH,
        "height": GRID_HEIGHT,
        "description": "Trace a safe route through a flooded neighborhood.",
    },
    {
        "id": "collapse",
        "label": "Building collapse",
        "width": GRID_WIDTH,
        "height": GRID_HEIGHT,
        "description": "Listen through unstable rubble for signs of life.",
    },
]


@dataclass
class Probe:
    id: str
    x: int
    y: int
    confidence: float


@dataclass
class MissionState:
    status: MissionStatus = "STANDBY"
    phase: MissionPhase = "explore"
    scenario: ScenarioId = "collapse"
    robot: tuple[int, int] = (0, 0)
    source: tuple[int, int] | None = None
    probes: list[Probe] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    confidence: float = 0.0
    demo_mode: bool = False
    noise_bias: float = 0.0
    last_auto_step: float = field(default_factory=monotonic)


_state = MissionState()


def scenario_presets() -> list[dict[str, str | int]]:
    return [dict(scenario) for scenario in SCENARIOS]


def confidence_at(
    point: tuple[int, int], source: tuple[int, int], noise: float
) -> float:
    distance = hypot(point[0] - source[0], point[1] - source[1])
    signal = 0.08 + 0.86 / (1 + distance / 2.75)
    return max(0.02, min(0.98, signal + noise))


def telemetry() -> dict[str, object]:
    return {
        "mission": {
            "status": _state.status,
            "phase": _state.phase,
            "scenario": _state.scenario,
            "probe_count": len(_state.probes),
            "confidence": _state.confidence,
        },
        "robot": {"x": _state.robot[0], "y": _state.robot[1]},
        "probes": [
            {
                "id": probe.id,
                "x": probe.x,
                "y": probe.y,
                "confidence": probe.confidence,
            }
            for probe in _state.probes
        ],
        "events": list(_state.events),
    }


def _record_event(message: str) -> None:
    _state.events.append(message)
    _state.events = _state.events[-8:]


def begin_mission(scenario: ScenarioId, demo: bool = False) -> None:
    global _state
    _state = MissionState(
        status="ACTIVE",
        scenario=scenario,
        source=DEMO_SOURCE if demo else (
            random.randrange(GRID_WIDTH), random.randrange(GRID_HEIGHT)
        ),
        demo_mode=demo,
        # A shared sensor bias adds uncertainty without changing distance ordering.
        noise_bias=0.0 if demo else random.uniform(-0.035, 0.035),
        events=["Mission started." if not demo else "Demo started."],
    )


def _advance() -> None:
    if _state.status != "ACTIVE":
        return

    if _state.phase == "explore":
        path = DEMO_PROBE_PATH if _state.demo_mode else SEARCH_PATH
        point = path[min(len(_state.probes), len(path) - 1)]
        _state.robot = point
        _state.phase = "knock"
        _record_event("Stopped.")
    elif _state.phase == "knock":
        _state.phase = "listen"
        _record_event("Knocked.")
    elif _state.phase == "listen":
        source = _state.source
        if source is None:
            return
        confidence = confidence_at(_state.robot, source, _state.noise_bias)
        _state.probes.append(
            Probe(
                id=f"P{len(_state.probes) + 1:02d}",
                x=_state.robot[0],
                y=_state.robot[1],
                confidence=confidence,
            )
        )
        _state.confidence = confidence
        _state.phase = "decide"
        _record_event("Listening.")
    else:
        _record_event("Choosing the next search point.")
        probe_limit = len(DEMO_PROBE_PATH) if _state.demo_mode else GRID_WIDTH
        if len(_state.probes) >= probe_limit or _state.confidence >= 0.92:
            _state.status = "DONE"
            _record_event("Mission complete.")
        else:
            _state.phase = "explore"


def pause_mission() -> None:
    if _state.status == "ACTIVE":
        _state.status = "PAUSED"
        _record_event("Paused.")


def resume_mission() -> None:
    if _state.status == "PAUSED":
        _state.status = "ACTIVE"
        _state.last_auto_step = monotonic()
        _record_event("Resumed.")


def reset_mission() -> None:
    global _state
    _state = MissionState()


def step_mission() -> None:
    _advance()


def tick_if_due() -> None:
    # One shared gate prevents extra WebSocket clients from speeding up a mission.
    now = monotonic()
    if _state.status == "ACTIVE" and now - _state.last_auto_step >= TICK_SECONDS:
        _state.last_auto_step = now
        _advance()