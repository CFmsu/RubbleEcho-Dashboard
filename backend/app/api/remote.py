from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.remote_drive import (
    drive_command,
    public_remote,
    request_collect,
    request_deploy,
    set_mode,
    set_sensor,
    set_servo,
    set_speed,
)

router = APIRouter()


class DriveBody(BaseModel):
    command: str


class SensorBody(BaseModel):
    sensor: str
    enabled: bool


class ModeBody(BaseModel):
    mode: str


class SpeedBody(BaseModel):
    level: int


class ServoBody(BaseModel):
    horn: str
    move: str
    speed: int = 3


@router.get("/api/remote")
async def remote_state() -> dict:
    return public_remote()


@router.post("/api/remote/drive")
async def remote_drive(body: DriveBody) -> dict:
    result = drive_command(body.command)
    if not result["ok"]:
        raise HTTPException(status_code=result["status"], detail=result)
    return result


@router.post("/api/remote/mode")
async def remote_mode(body: ModeBody) -> dict:
    result = set_mode(body.mode)
    if not result["ok"]:
        raise HTTPException(status_code=result["status"], detail=result)
    return result


@router.post("/api/remote/speed")
async def remote_speed(body: SpeedBody) -> dict:
    result = set_speed(body.level)
    if not result["ok"]:
        raise HTTPException(status_code=result["status"], detail=result)
    return result


@router.post("/api/remote/servo")
async def remote_servo(body: ServoBody) -> dict:
    result = set_servo(body.horn, body.move, body.speed)
    if not result["ok"]:
        raise HTTPException(status_code=result["status"], detail=result)
    return result


@router.post("/api/remote/deploy")
async def remote_deploy() -> dict:
    return request_deploy()


@router.post("/api/remote/collect")
async def remote_collect() -> dict:
    return request_collect()


@router.post("/api/remote/sensor")
async def remote_sensor(body: SensorBody) -> dict:
    result = set_sensor(body.sensor, body.enabled)
    if not result["ok"]:
        raise HTTPException(status_code=result["status"], detail=result)
    return result
