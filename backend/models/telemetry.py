from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from models.mission import ComparisonResult, MissionEvent, MissionView, ProbePoint, RobotState, SearchDecision
from models.sensors import SensorBundle


class HardwareItem(BaseModel):
    name: str
    status: str


class TelemetryMessage(BaseModel):
    type: Literal["telemetry"] = "telemetry"
    timestamp: float
    mission: MissionView
    robot: RobotState
    sensors: SensorBundle
    probability_map: list[list[float]]
    probes: list[ProbePoint]
    decision: SearchDecision
    events: list[MissionEvent]
    comparison: Optional[ComparisonResult] = None
    hardware: list[HardwareItem]
    mode: Literal["simulation"] = "simulation"
