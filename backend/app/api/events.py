from fastapi import APIRouter

from app.services.mission import snapshot

router = APIRouter()


@router.get("/api/events")
async def events() -> list[dict]:
    return snapshot()["events"]
