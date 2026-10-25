from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/api/audio/device")
async def audio_device() -> dict:
    from app.drivers.respeaker import device_report

    return device_report()


@router.post("/api/audio/listen")
async def audio_listen() -> dict:
    from app.audio.engine import start_listener

    result = start_listener()
    if not result["ok"]:
        raise HTTPException(status_code=409, detail=result)
    return result


@router.post("/api/audio/stop")
async def audio_stop() -> dict:
    from app.audio.engine import stop_listener

    return stop_listener()
