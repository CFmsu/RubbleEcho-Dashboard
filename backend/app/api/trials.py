import io
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.auth import require_operator
from app.persistence.store import load_trial
from app.services.mission import annotate, export_trial, ground_truth, start_trial
from app.state import get_state

router = APIRouter()


class TrialStart(BaseModel):
    mode: str
    fixture: str | None = "sample_trial"


class TrialNote(BaseModel):
    sand_depth: str | None = None
    cover_depth_cm: float | None = None
    operator_label: str | None = None
    notes: str | None = None
    actual_source: str | None = None
    release_to_overlay: bool = False


@router.post("/api/trials/start")
async def begin(body: TrialStart, _: None = Depends(require_operator)) -> dict:
    result = start_trial(body.mode, body.fixture)
    if not result["ok"]:
        raise HTTPException(status_code=result["status"], detail=result)
    return result


@router.get("/api/trials/{trial_id}")
async def read_trial(trial_id: str) -> dict:
    state = get_state()
    trial = state.trial if state.trial and state.trial_id == trial_id else load_trial(trial_id)
    if trial is None:
        raise HTTPException(status_code=404, detail={"error": "trial not found"})
    public = dict(trial)
    public["source_recorded"] = public.get("actual_source") not in {None, "", "not_recorded"}
    public.pop("actual_source", None)
    public.pop("actual_source_disclosed", None)
    return public


@router.post("/api/trials/{trial_id}/annotate")
async def note(
    trial_id: str,
    body: TrialNote,
    _: None = Depends(require_operator),
) -> dict:
    updated = annotate(trial_id, body.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail={"error": "trial not found"})
    return updated


@router.post("/api/trials/{trial_id}/finish")
async def finish(trial_id: str, _: None = Depends(require_operator)) -> dict:
    state = get_state()
    if state.trial_id != trial_id or state.trial is None:
        raise HTTPException(status_code=404, detail={"error": "trial not found"})
    state.trial["finished"] = True
    if state.phase not in {"ESTOP", "FAULT"}:
        state.phase = "COMPLETE"
    return {"trial_id": trial_id, "finished": True, "mission_phase": state.phase}


@router.get("/api/trials/{trial_id}/ground-truth")
async def overlay(trial_id: str, _: None = Depends(require_operator)) -> dict:
    result = ground_truth(trial_id)
    if result is None:
        raise HTTPException(status_code=404, detail={"error": "trial not found"})
    return result


@router.get("/api/trials/{trial_id}/export")
async def export(
    trial_id: str,
    format: str = "zip",
    _: None = Depends(require_operator),
) -> Response:
    payload = export_trial(trial_id)
    if payload is None:
        raise HTTPException(status_code=404, detail={"error": "trial not found"})
    if format == "zip":
        return Response(
            content=payload,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{trial_id}.zip"'},
        )
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if format == "json":
            body = archive.read("manifest.json")
            return Response(content=body, media_type="application/json")
        if format == "csv":
            body = archive.read("measurements.csv")
            return Response(content=body, media_type="text/csv")
    raise HTTPException(status_code=400, detail={"error": "format must be zip, json, or csv"})
