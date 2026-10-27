from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.auth import require_operator
from app.services.mission import arm_solenoid, estop, hold, knock_request, snapshot, submit_command
from app.services.sim_run import halt_run, media_file, start_run
from app.state import get_state

router = APIRouter()


class CommandBody(BaseModel):
    command_id: str
    type: str
    distance_cm: float | None = None
    turn_deg: float | None = None
    target_x_cm: float | None = None
    target_y_cm: float | None = None


class KnockBody(BaseModel):
    width_ms: int = Field(default=200, ge=1, le=5000)
    consent: bool = False
    rover_moving: bool = False
    now_ms: int = 0
    arm_first: bool = False


@router.get("/api/mission/state")
async def mission_state() -> dict:
    current = snapshot()
    return {
        "mode": current["mode"],
        "mission_phase": current["mission_phase"],
        "safety_state": current["safety_state"],
        "badge": current["badge"],
        "trial_id": current["trial_id"],
        "output_energized": False,
    }


@router.post("/api/mission/run")
async def mission_run() -> dict:
    return start_run()


@router.post("/api/mission/halt")
async def mission_halt() -> dict:
    return halt_run()


@router.get("/api/simulation/camera.png")
async def simulation_camera(point: str | None = None) -> Response:
    path = media_file("camera", point)
    if path is None:
        raise HTTPException(status_code=404, detail={"error": "no simulation frame"})
    return Response(content=path.read_bytes(), media_type="image/png")


@router.get("/api/simulation/audio.wav")
async def simulation_audio() -> Response:
    path = media_file("audio")
    if path is None:
        raise HTTPException(status_code=404, detail={"error": "no simulation audio"})
    return Response(content=path.read_bytes(), media_type="audio/wav")


@router.post("/api/mission/estop")
async def mission_estop() -> dict:
    return estop("operator_estop")


@router.post("/api/mission/stop")
async def mission_stop() -> dict:
    return hold("operator_stop")


@router.post("/api/operations/clear")
async def clear_view(_: None = Depends(require_operator)) -> dict:
    from app.services.radar_link import stop_radar

    stop_radar()
    preserved = get_state().trial_id
    get_state().reset()
    return {
        "cleared": True,
        "preserved_trial_id": preserved,
        "exports_deleted": False,
    }


@router.post("/api/operations/command")
async def operations_command(
    body: CommandBody,
    _: None = Depends(require_operator),
) -> dict:
    return submit_command(body.model_dump())


@router.post("/api/operations/arm")
async def operations_arm(
    consent: bool = False,
    _: None = Depends(require_operator),
) -> dict:
    return arm_solenoid(consent)


@router.post("/api/operations/knock")
async def operations_knock(
    body: KnockBody,
    _: None = Depends(require_operator),
) -> dict:
    if body.arm_first:
        arm_solenoid(body.consent)
    result = knock_request(body.width_ms, body.consent, body.rover_moving, body.now_ms)
    result["output_energized"] = False
    return result
