from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.remote_drive import drive_command, public_remote, set_mode, set_sensor

router = APIRouter()


class DriveBody(BaseModel):
    command: str


class SensorBody(BaseModel):
    sensor: str
    enabled: bool


class ModeBody(BaseModel):
    mode: str


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


@router.post("/api/remote/sensor")
async def remote_sensor(body: SensorBody) -> dict:
    result = set_sensor(body.sensor, body.enabled)
    if not result["ok"]:
        raise HTTPException(status_code=result["status"], detail=result)
    return result
