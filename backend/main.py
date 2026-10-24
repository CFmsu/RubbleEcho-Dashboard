import asyncio

from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import simulation
from app.api.router import api_router
from app.services.mission import note_legacy_reset, note_legacy_start


class MissionCommand(BaseModel):
    scenario: simulation.ScenarioId = "collapse"


app = FastAPI(title="RubbleEcho Simulation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Operator-Token"],
)
app.include_router(api_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/scenarios")
async def scenarios() -> list[dict[str, str | int]]:
    return simulation.scenario_presets()


@app.post("/api/mission/start")
async def start_mission(
    command: MissionCommand = Body(default=MissionCommand()),
) -> dict[str, object]:
    simulation.begin_mission(command.scenario)
    note_legacy_start()
    return simulation.telemetry()


@app.post("/api/mission/demo")
async def start_demo(
    command: MissionCommand = Body(default=MissionCommand()),
) -> dict[str, object]:
    simulation.begin_mission(command.scenario, demo=True)
    note_legacy_start()
    return simulation.telemetry()


@app.post("/api/mission/pause")
async def pause_mission() -> dict[str, object]:
    simulation.pause_mission()
    return simulation.telemetry()


@app.post("/api/mission/resume")
async def resume_mission() -> dict[str, object]:
    simulation.resume_mission()
    return simulation.telemetry()


@app.post("/api/mission/reset")
async def reset_mission() -> dict[str, object]:
    simulation.reset_mission()
    note_legacy_reset()
    return simulation.telemetry()


@app.post("/api/mission/step")
async def step_mission() -> dict[str, object]:
    simulation.step_mission()
    return simulation.telemetry()


@app.websocket("/ws/telemetry")
async def telemetry_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            simulation.tick_if_due()
            await websocket.send_json(simulation.telemetry())
            await asyncio.sleep(simulation.TICK_SECONDS)
    except WebSocketDisconnect:
        return