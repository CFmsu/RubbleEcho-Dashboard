from fastapi import APIRouter

from app.api import ai, audio, cameras, devices, events, health, missions, stream, trials

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(audio.router)
api_router.include_router(devices.router)
api_router.include_router(events.router)
api_router.include_router(missions.router)
api_router.include_router(cameras.router)
api_router.include_router(ai.router)
api_router.include_router(trials.router)
api_router.include_router(stream.router)
