import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.state import controller

logger = logging.getLogger("rubbleecho.telemetry")
router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.add(websocket)
        await websocket.send_json(controller.snapshot().model_dump(mode="json"))

    def disconnect(self, websocket: WebSocket) -> None:
        self.active.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        dead: list[WebSocket] = []
        for websocket in list(self.active):
            try:
                await websocket.send_json(payload)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(websocket)


manager = ConnectionManager()


@router.websocket("/ws/telemetry")
async def telemetry_socket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        logger.info("telemetry client disconnected")
        manager.disconnect(websocket)


async def telemetry_loop() -> None:
    while True:
        try:
            if controller.status == "ACTIVE":
                controller.tick(0.125 * controller.speed)
                await manager.broadcast(controller.snapshot().model_dump(mode="json"))
                await asyncio.sleep(0.125)
            else:
                await manager.broadcast(controller.snapshot().model_dump(mode="json"))
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("telemetry loop error")
            await asyncio.sleep(0.5)
