from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.auth import require_operator
from app.services.live_run import authorize_motion, open_pi_session, start_grid
from app.services.mission import arm_solenoid, estop, hold, knock_request, snapshot, submit_command
from app.services.pi_ingest import ingest
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


class HardwareBody(BaseModel):
    authorize_motion: bool = False


class PiBody(BaseModel):
    source: str = "raspberry_pi_4"
    lines: list[str] | None = None
    radar: dict | None = None
    ultrasonic: dict | None = None
    piezo: dict | None = None
    audio: dict | None = None
    encoders: dict | None = None
    camera_id: str | None = None
    camera_jpeg_base64: str | None = None
    reason: bool = False
    cell: str | None = None


@router.post("/api/mission/run")
async def mission_run() -> dict:
    return start_run()


@router.post("/api/mission/live")
async def mission_live() -> dict:
    return open_pi_session()


@router.post("/api/mission/hardware")
async def mission_hardware(body: HardwareBody) -> dict:
    if not body.authorize_motion:
        raise HTTPException(
            status_code=403,
            detail={
                "ok": False,
                "error": "Physical motion requires authorize_motion true. POST /api/mission/live waits for the Pi without moving.",
            },
        )
    return authorize_motion()


@router.post("/api/mission/grid")
async def mission_grid() -> dict:
    return start_grid()


class SweepBody(BaseModel):
    beams: list[dict] = []


class LinkBody(BaseModel):
    lines: list[str] = []


@router.get("/api/pi/sweep")
async def pi_sweep_status() -> dict:
    from app.services.grid_route import sweep_status

    return sweep_status()


@router.post("/api/pi/sweep")
async def pi_sweep(body: SweepBody) -> dict:
    from app.services.rover_track import apply_pi_sweep

    result = apply_pi_sweep(body.beams)
    if not result["ok"]:
        raise HTTPException(status_code=409, detail=result)
    return result


@router.get("/api/pi/operator")
async def pi_operator_poll() -> dict:
    from app.services.pi_link import take_operator

    return {"jobs": take_operator()}


@router.get("/api/pi/link")
async def pi_link_poll() -> dict:
    from app.services.pi_link import take_commands

    return {"commands": take_commands()}


@router.post("/api/pi/link")
async def pi_link_lines(body: LinkBody) -> dict:
    from app.services.pi_link import accept_lines

    return {"ok": True, "applied": accept_lines(body.lines)}


@router.post("/api/pi/ingest")
async def pi_ingest(body: PiBody) -> dict:
    result = ingest(body.model_dump())
    if not result["ok"]:
        raise HTTPException(status_code=result["status"], detail=result)
    return result


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
    if path is not None:
        return Response(content=path.read_bytes(), media_type="audio/wav")
    from app.services.mic_mimic import microphone_wav

    raw = microphone_wav(get_state())
    if raw is None:
        raise HTTPException(status_code=404, detail={"error": "no audio"})
    return Response(content=raw, media_type="audio/wav")


@router.get("/api/microphone/audio.wav")
async def microphone_audio() -> Response:
    from app.services.mic_mimic import microphone_wav

    raw = microphone_wav(get_state())
    if raw is None:
        raise HTTPException(status_code=404, detail={"error": "no audio"})
    return Response(content=raw, media_type="audio/wav")


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
