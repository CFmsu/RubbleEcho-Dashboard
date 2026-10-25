from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/api/radar/device")
async def radar_device() -> dict:
    from app.services.radar_link import device_report

    return device_report()


@router.post("/api/radar/listen")
async def radar_listen() -> dict:
    from app.services.radar_link import start_listener

    result = start_listener()
    if not result["ok"]:
        raise HTTPException(status_code=409, detail=result)
    return result


@router.post("/api/radar/dummy")
async def radar_dummy() -> dict:
    from app.services.radar_link import start_dummy

    return start_dummy()


@router.post("/api/radar/stop")
async def radar_stop() -> dict:
    from app.services.radar_link import stop_radar

    return stop_radar()
