from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.auth import require_operator
from app.services.mission import capture_camera, snapshot
from app.services.pi_ingest import posted_frame

router = APIRouter()


@router.get("/api/cameras")
async def cameras() -> dict:
    current = snapshot()
    return {
        "cameras": current["cameras"],
        "streaming_camera_count": current["streaming_camera_count"],
        "camera_count": current["camera_count"],
        "calibration": current["calibration"],
    }


@router.post("/api/camera/{camera_id}/capture")
async def capture(camera_id: str, _: None = Depends(require_operator)) -> dict:
    result = capture_camera(camera_id)
    if not result["ok"]:
        raise HTTPException(status_code=result["status"], detail=result)
    return result


@router.get("/api/camera/{camera_id}/latest")
async def latest(camera_id: str) -> Response:
    frame = posted_frame(camera_id)
    if frame is None:
        result = capture_camera(camera_id)
        raise HTTPException(status_code=result["status"], detail=result)
    return Response(content=frame, media_type="image/jpeg")
