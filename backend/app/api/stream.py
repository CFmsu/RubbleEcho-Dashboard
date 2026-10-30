import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.mission import apply_link_lost, snapshot

router = APIRouter()
_clients = 0


@router.websocket("/ws/operations")
async def operations_socket(websocket: WebSocket) -> None:
    global _clients
    await websocket.accept()
    from app.state import get_state

    _clients += 1
    get_state().operator_link = True
    try:
        while True:
            await websocket.send_json(snapshot())
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass
    finally:
        _clients = max(0, _clients - 1)
        if _clients == 0:
            apply_link_lost()
