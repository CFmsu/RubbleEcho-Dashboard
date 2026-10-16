"""RubbleEcho simulation backend."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from api.field import field_loop
from api.field import router as field_router
from api.field import ws_router as field_ws_router
from api.mission import router as mission_router
from api.system import router as system_router
from api.telemetry import router as telemetry_router
from api.telemetry import telemetry_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("rubbleecho")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from hardware.serial_bridge import bridge

    bridge.set_ultrasonic_enabled(True)
    telemetry_task = asyncio.create_task(telemetry_loop())
    field_task = asyncio.create_task(field_loop())
    logger.info("RubbleEcho backend online")
    yield
    field_task.cancel()
    telemetry_task.cancel()
    with suppress(asyncio.CancelledError):
        await field_task
    with suppress(asyncio.CancelledError):
        await telemetry_task
    bridge.disconnect()


app = FastAPI(
    title="RubbleEcho",
    summary="RubbleEcho rover dashboard and simulation.",
    version="0.1.0",
    lifespan=lifespan,
)

origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router, prefix="/api")
app.include_router(mission_router, prefix="/api")
app.include_router(field_router, prefix="/api")
app.include_router(telemetry_router)
app.include_router(field_ws_router)


@app.get("/")
def root() -> dict:
    return {
        "service": "rubbleecho",
        "mode": "simulation",
        "health": "/api/health",
        "docs": "/docs",
    }
