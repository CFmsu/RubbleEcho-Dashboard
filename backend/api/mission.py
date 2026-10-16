from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.lab import run_stimulus
from core.state import controller
from models.mission import SimulationConfig
from simulation.scenarios import list_scenarios

router = APIRouter()


class SpeedRequest(BaseModel):
    speed: float = Field(ge=0.5, le=10)


class LabRequest(BaseModel):
    stimulus: str
    seed: int = 7


@router.get("/mission")
def get_mission() -> dict:
    return controller.snapshot().model_dump(mode="json")


@router.post("/mission/start")
def start_mission() -> dict:
    controller.start(demo=False)
    return controller.snapshot().model_dump(mode="json")


@router.post("/mission/demo")
def start_demo() -> dict:
    controller.start(demo=True)
    return controller.snapshot().model_dump(mode="json")


@router.post("/mission/pause")
def pause_mission() -> dict:
    controller.pause()
    return controller.snapshot().model_dump(mode="json")


@router.post("/mission/resume")
def resume_mission() -> dict:
    controller.resume()
    return controller.snapshot().model_dump(mode="json")


@router.post("/mission/reset")
def reset_mission() -> dict:
    controller.reset()
    return controller.snapshot().model_dump(mode="json")


@router.post("/mission/step")
def step_mission() -> dict:
    try:
        controller.step()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return controller.snapshot().model_dump(mode="json")


@router.post("/mission/speed")
def set_speed(body: SpeedRequest) -> dict:
    controller.set_speed(body.speed)
    return {"speed": controller.speed}


@router.get("/mission/map")
def mission_map() -> dict:
    return {
        "width": controller.config.width,
        "height": controller.config.height,
        "probability_map": controller.engine.belief.get_map(),
        "probes": [probe.model_dump() for probe in controller.probes],
    }


@router.get("/mission/events")
def mission_events() -> dict:
    return {"events": [event.model_dump() for event in controller.events]}


@router.get("/sensors/latest")
def latest_sensors() -> dict:
    return controller.snapshot().sensors.model_dump(mode="json")


@router.get("/scenarios")
def scenarios() -> dict:
    return {"scenarios": list_scenarios()}


@router.get("/simulation/config")
def get_config() -> dict:
    return {
        "config": controller.config.model_dump(),
        "ground_truth_hidden_from_search": True,
        "note": "Ground truth is exposed only on this setup endpoint. It is not included in telemetry.",
    }


@router.post("/simulation/config")
def set_config(config: SimulationConfig) -> dict:
    try:
        controller.configure(config)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "config": controller.config.model_dump(),
        "ground_truth_hidden_from_search": True,
    }


@router.post("/lab/stimulus")
def lab_stimulus(body: LabRequest) -> dict:
    known = {"knock", "human_tap", "noise_burst", "cavity_response", "weak_response", "strong_response"}
    if body.stimulus not in known:
        raise HTTPException(status_code=422, detail="Unknown stimulus.")
    return run_stimulus(body.stimulus, body.seed)
