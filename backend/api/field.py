"""Real-world observations: photographs, Nebius inference, and hardware state.

This router does not read or write the simulated mission. Demo telemetry stays
on /ws/telemetry. Field data stays here.
"""

from __future__ import annotations

import asyncio
import os
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from field.grid import CELL_IDS
from field.images import ImageDecodeError, decode_upload
from field.inference import analyze_image, reason_about
from field.schema import PHOTO_LIMITATION, GridCell, ReasoningResult
from field.store import ALLOWED_TYPES, store
from hardware.serial_bridge import bridge, list_ports
from integrations.nebius.client import NebiusClient, NebiusError
from field.models_catalog import accepts_images

router = APIRouter()
ws_router = APIRouter()

WARNINGS = [
    PHOTO_LIMITATION,
    "Classifications describe the visible surface only.",
    "ESP32 button events are MANUAL HARDWARE TEST EVENTS, not physiological detections.",
    "An HC-SR04 measures distance to a nearby exposed surface. It cannot detect people through rubble.",
    "Piezo, mmWave radar, thermal camera, and a microphone array are not connected.",
]

_loop: asyncio.AbstractEventLoop | None = None
_clients: set[WebSocket] = set()


class ModeBody(BaseModel):
    operating_mode: Literal["demo", "real"]


class CellCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell: str
    classification: Literal["debris_covered", "obstructed", "clear_surface", "possible_opening", "uncertain"]
    observation: str = ""
    uncertainty: Literal["low", "medium", "high"] = "medium"


class ConnectBody(BaseModel):
    port: str = Field(min_length=1, max_length=64)
    baud: int = 115200


def field_snapshot() -> dict:
    hardware = bridge.snapshot()
    hardware["ports"] = [port.model_dump() for port in list_ports()]
    return {
        "type": "field",
        "operating_mode": store.operating_mode(),
        "nebius_configured": bool(os.getenv("NEBIUS_API_KEY", "").strip()),
        "warnings": WARNINGS,
        "cells": list(CELL_IDS),
        "observations": [item.model_dump() for item in store.list_observations()],
        "hardware": hardware,
    }


async def broadcast_field() -> None:
    payload = field_snapshot()
    dead: list[WebSocket] = []
    for websocket in list(_clients):
        try:
            await websocket.send_json(payload)
        except Exception:
            dead.append(websocket)
    for websocket in dead:
        _clients.discard(websocket)


def publish_field() -> None:
    if _loop is None or not _loop.is_running():
        return
    asyncio.run_coroutine_threadsafe(broadcast_field(), _loop)


def bind_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop
    bridge._on_change = publish_field


async def field_loop() -> None:
    bind_loop(asyncio.get_running_loop())
    while True:
        try:
            await broadcast_field()
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(0.5)


def _observation_or_404(observation_id: str):
    if len(observation_id) != 32 or any(char not in "0123456789abcdef" for char in observation_id):
        raise HTTPException(status_code=404, detail="observation not found")
    observation = store.get(observation_id)
    if observation is None:
        raise HTTPException(status_code=404, detail="observation not found")
    return observation


@router.get("/field")
def get_field() -> dict:
    return field_snapshot()


@router.get("/mode")
def get_mode() -> dict:
    return {"operating_mode": store.operating_mode()}


@router.post("/mode")
def set_mode(body: ModeBody) -> dict:
    store.set_operating_mode(body.operating_mode)
    publish_field()
    return {"operating_mode": store.operating_mode()}


@router.post("/observations")
async def create_observation(
    file: UploadFile = File(...),
    source: str = Form("iphone_camera"),
) -> dict:
    media_type = (file.content_type or "").split(";")[0].strip().lower()
    filename = file.filename or "upload"
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if media_type not in ALLOWED_TYPES:
        guessed = { "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "heic": "image/heic", "heif": "image/heif" }.get(suffix)
        if guessed is None:
            raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or HEIC photograph.")
        media_type = guessed
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="The upload was empty.")
    if len(payload) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Photograph must be 20 MB or smaller.")
    try:
        display, width, height = decode_upload(payload, media_type)
    except ImageDecodeError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    clean_source = "".join(char for char in source if char.isalnum() or char in {"_", "-"})[:64] or "iphone_camera"
    observation = store.create(
        filename=filename,
        media_type=media_type,
        original=payload,
        display_jpeg=display,
        width=width,
        height=height,
        source=clean_source,
    )
    publish_field()
    return observation.model_dump()


@router.get("/observations/{observation_id}/image")
def observation_image(observation_id: str) -> FileResponse:
    _observation_or_404(observation_id)
    path = store.image_path(observation_id)
    if path is None:
        raise HTTPException(status_code=404, detail="image file is missing")
    return FileResponse(path, media_type="image/jpeg")


@router.post("/observations/{observation_id}/analyze")
def analyze_observation(observation_id: str) -> dict:
    observation = _observation_or_404(observation_id)
    path = store.image_path(observation.id)
    if path is None:
        raise HTTPException(status_code=404, detail="image file is missing")
    analysis = analyze_image(path.read_bytes(), "image/jpeg")
    saved = store.save_analysis(observation.id, analysis)
    publish_field()
    return saved.model_dump()


@router.post("/observations/{observation_id}/reason")
def reason_observation(observation_id: str) -> dict:
    observation = _observation_or_404(observation_id)
    usable = [cell.model_dump() for cell in observation.cells if cell.source != "unanalyzed"]
    if not usable:
        saved = store.save_reasoning(
            observation.id,
            ReasoningResult(
                request_status="failed",
                error="No visual observations to reason over. Run vision analysis or label cells manually.",
            ),
        )
        publish_field()
        return saved.model_dump()
    path = store.image_path(observation.id)
    image = path.read_bytes() if path is not None else None
    reasoning = reason_about(usable, image_bytes=image, media_type="image/jpeg")
    saved = store.save_reasoning(observation.id, reasoning)
    publish_field()
    return saved.model_dump()


@router.post("/observations/{observation_id}/cells")
def correct_cell(observation_id: str, body: CellCorrection) -> dict:
    _observation_or_404(observation_id)
    try:
        cell = GridCell(
            cell=body.cell,
            classification=body.classification,
            observation=body.observation,
            uncertainty=body.uncertainty,
            source="manual_correction",
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Cell correction does not match the visual schema.") from exc
    saved = store.correct_cell(observation_id, cell)
    publish_field()
    return saved.model_dump()


@router.get("/hardware/ports")
def hardware_ports() -> dict:
    return {"ports": [port.model_dump() for port in list_ports()]}


@router.post("/hardware/connect")
def hardware_connect(body: ConnectBody) -> dict:
    known = {port.device for port in list_ports()}
    if body.port not in known:
        raise HTTPException(status_code=404, detail=f"{body.port} is not an available COM port")
    if body.baud not in (9600, 19200, 38400, 57600, 115200):
        raise HTTPException(status_code=422, detail="Choose 9600, 19200, 38400, 57600, or 115200 baud.")
    try:
        bridge.connect(body.port, baud=body.baud)
    except Exception as exc:
        message = str(exc)
        if "Access is denied" in message or "PermissionError" in message:
            message = f"{body.port} is in use. Close the Arduino Serial Monitor, then connect again."
        raise HTTPException(status_code=503, detail=f"Could not open {body.port}: {message}") from exc
    publish_field()
    return field_snapshot()["hardware"]


@router.post("/hardware/disconnect")
def hardware_disconnect() -> dict:
    bridge.disconnect()
    publish_field()
    return field_snapshot()["hardware"]


@router.get("/inference/models")
def inference_models() -> dict:
    client = NebiusClient()
    if not client.configured:
        raise HTTPException(
            status_code=503,
            detail="NEBIUS_API_KEY is not set. Add it to .env and restart the backend. Manual labels still work.",
        )
    try:
        models = client.list_models()
    except NebiusError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "models": [
            {"id": model.id, "accepts_images": accepts_images(model), "input_modalities": list(model.input_modalities)}
            for model in models
            if model.id
        ]
    }


@ws_router.websocket("/ws/field")
async def field_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    _clients.add(websocket)
    try:
        await websocket.send_json(field_snapshot())
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _clients.discard(websocket)
    except Exception:
        _clients.discard(websocket)
