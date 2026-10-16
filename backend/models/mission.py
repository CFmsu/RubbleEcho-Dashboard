from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


SearchStrategyName = Literal["grid", "adaptive"]
MissionStatus = Literal["IDLE", "ACTIVE", "PAUSED", "COMPLETE"]
EventLevel = Literal["info", "warn", "alert", "good"]


class SimulationConfig(BaseModel):
    width: int = Field(default=12, ge=6, le=24)
    height: int = Field(default=12, ge=6, le=24)
    survivor_x: float = 7.2
    survivor_y: float = 6.4
    noise_level: float = Field(default=0.18, ge=0, le=1)
    response_probability: float = Field(default=0.82, ge=0, le=1)
    sensor_reliability: float = Field(default=0.9, ge=0, le=1)
    search_strategy: SearchStrategyName = "adaptive"
    seed: int = 42
    scenario: str = "structural_collapse"
    speed: float = Field(default=1.0, ge=0.5, le=10)
    demo_mode: bool = False

    @model_validator(mode="after")
    def keep_survivor_inside(self) -> "SimulationConfig":
        self.survivor_x = float(min(max(self.survivor_x, 0.4), self.width - 0.4))
        self.survivor_y = float(min(max(self.survivor_y, 0.4), self.height - 0.4))
        return self


class ProbePoint(BaseModel):
    id: str
    x: float
    y: float
    confidence: float
    audio_state: str
    vibration_confidence: float
    cavity_confidence: float
    is_confirmation: bool = False


class RobotState(BaseModel):
    x: float
    y: float
    heading: float
    velocity: float
    battery: float
    state: str
    phase: str
    current_target_x: Optional[float] = None
    current_target_y: Optional[float] = None
    probe_count: int
    distance_travelled: float
    trail: list[list[float]] = Field(default_factory=list)


class MissionEvent(BaseModel):
    time: float
    message: str
    level: EventLevel = "info"


class FusionResult(BaseModel):
    audio: float
    vibration: float
    cavity: float
    visual: float
    combined: float
    weights: dict[str, float]


class SearchDecision(BaseModel):
    observation: str
    decision: str
    reason: str
    confidence: float
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    provider: str = "SIMULATED"


class StrategyStats(BaseModel):
    measurements: int
    distance_travelled: float
    simulated_minutes: float
    found: bool


class ComparisonResult(BaseModel):
    grid: StrategyStats
    adaptive: StrategyStats
    note: str = "SIMULATED RESULTS — not validated physical performance."


class CandidateLocation(BaseModel):
    x: float
    y: float
    confidence: float
    status: str = "Awaiting Rescue Team Verification"


class MissionView(BaseModel):
    id: str
    status: MissionStatus
    scenario: str
    scenario_label: str
    robot_state: str
    runtime: float
    probe_count: int
    highest_confidence: float
    phase: str
    phase_progress: float
    demo_mode: bool
    search_strategy: SearchStrategyName
    speed: float
    width: int
    height: int
    activity_step: str = "MOVE"
    candidate: Optional[CandidateLocation] = None
    outcome: Optional[str] = None
