from fastapi import APIRouter

from app.services.mission import snapshot

router = APIRouter()


@router.get("/api/devices")
async def devices() -> list[dict]:
    return snapshot()["devices"]
