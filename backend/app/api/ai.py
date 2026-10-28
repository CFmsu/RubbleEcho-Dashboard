import asyncio

from fastapi import APIRouter, Depends

from app.ai.nebius_client import ai_status, healthcheck
from app.api.auth import require_operator
from app.services.mission import request_reason

router = APIRouter()


@router.get("/api/ai/status")
async def status() -> dict:
    current = ai_status()
    current["nvidia_online"] = False
    return current


@router.post("/api/ai/healthcheck")
async def check(_: None = Depends(require_operator)) -> dict:
    result = await asyncio.to_thread(healthcheck)
    result["nvidia_online"] = bool(result.get("nvidia_online"))
    return result


@router.post("/api/ai/reason")
async def reason(_: None = Depends(require_operator)) -> dict:
    result = await asyncio.to_thread(request_reason)
    result["nvidia_online"] = bool(result.get("nvidia_online"))
    return result
