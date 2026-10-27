import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.mission import apply_link_lost, snapshot

router = APIRouter()


@router.websocket("/ws/operations")
async def operations_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    from app.state import get_state

    get_state().operator_link = True
    try:
        while True:
            await websocket.send_json(snapshot())
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        apply_link_lost()
