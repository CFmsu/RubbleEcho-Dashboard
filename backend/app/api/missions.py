from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.auth import require_operator
from app.services.mission import arm_solenoid, estop, hold, knock_request, snapshot, submit_command
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
    width_ms: int = Field(default=40, ge=1, le=5000)
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


@router.post("/api/mission/estop")
async def mission_estop() -> dict:
    return estop("operator_estop")


@router.post("/api/mission/stop")
async def mission_stop() -> dict:
    return hold("operator_stop")


@router.post("/api/operations/clear")
async def clear_view(_: None = Depends(require_operator)) -> dict:
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
