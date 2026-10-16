import os

from fastapi import APIRouter

from field.store import store

router = APIRouter()


@router.get("/health")
def health() -> dict:
    operating_mode = store.operating_mode()
    return {
        "status": "ok",
        "service": "rubbleecho",
        "mode": "simulation" if operating_mode == "demo" else "real",
        "operating_mode": operating_mode,
        "nebius_configured": bool(os.getenv("NEBIUS_API_KEY", "").strip()),
        "ultrasonic_enabled": os.getenv("RUBBLEECHO_ULTRASONIC_ENABLED", "").strip().lower() in {"1", "true", "yes"},
        "version": "0.2.0",
    }
