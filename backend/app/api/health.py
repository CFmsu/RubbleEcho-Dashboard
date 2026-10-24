from fastapi import APIRouter

from app.config.geometry import load_geometry
from app.services.mission import snapshot

router = APIRouter()


@router.get("/api/system/status")
async def system_status() -> dict:
    current = snapshot()
    return {
        "badge": current["badge"],
        "mode": current["mode"],
        "system_live": current["system_live"],
        "safety_state": current["safety_state"],
        "mission_phase": current["mission_phase"],
        "nvidia_online": current["nvidia_online"],
        "streaming_camera_count": current["streaming_camera_count"],
        "camera_count": current["camera_count"],
    }


@router.get("/api/config/geometry")
async def geometry() -> dict:
    return load_geometry()


@router.get("/api/operations/snapshot")
async def operations_snapshot() -> dict:
    return snapshot()
