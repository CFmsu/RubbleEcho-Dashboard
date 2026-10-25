from fastapi import APIRouter

from app.services.search_plan import apply_obstacle, apply_signal, plan_from_photo

router = APIRouter()


@router.post("/api/search/plan")
async def search_plan() -> dict:
    return plan_from_photo()


@router.post("/api/search/obstacle")
async def search_obstacle() -> dict:
    return apply_obstacle()


@router.post("/api/search/signal")
async def search_signal() -> dict:
    return apply_signal()
