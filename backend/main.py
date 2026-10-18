import asyncio

from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

import simulation


class MissionCommand(BaseModel):
    scenario: simulation.ScenarioId = "collapse"


app = FastAPI(title="RubbleEcho Simulation API")


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
    return simulation.telemetry()


@app.post("/api/mission/demo")
async def start_demo(
    command: MissionCommand = Body(default=MissionCommand()),
) -> dict[str, object]:
    simulation.begin_mission(command.scenario, demo=True)
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