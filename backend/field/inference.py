"""Run vision analysis and Nemotron reasoning for one stored photograph."""

from __future__ import annotations

import base64
import os

from field.models_catalog import accepts_images, select_reasoning_model, select_vision_model
from field.schema import (
    PHOTO_LIMITATION,
    ReasoningResult,
    VisionAnalysis,
    VisionPayload,
    validate_reasoning,
    validate_vision,
)
from integrations.nebius.client import NebiusClient, NebiusError

VISION_INSTRUCTIONS = """You inspect one photograph of a debris scene. The photo is overlaid with a 4 by 4 grid.
Columns A B C D run from left to right. Rows 1 2 3 4 run from top to bottom.
A1 is the top-left cell. D4 is the bottom-right cell. B1 is immediately right of A1. A2 is immediately below A1.

For every cell, describe only what is visible in that cell and classify it as exactly one of:
debris_covered, obstructed, clear_surface, possible_opening, uncertain.

Rules:
- debris_covered: loose rubble, broken material, or dust is visibly covering the surface.
- obstructed: a solid object blocks the view of the surface behind it.
- clear_surface: the surface in that cell looks exposed and relatively unobstructed.
- possible_opening: a visible gap, cavity mouth, or hole is in the cell. This is not evidence of a person.
- uncertain: the cell is too dark, blurred, or ambiguous.
- Do not infer buried people, vital signs, heat, distance, or any sensor reading.
- Do not invent a confidence score.
- Return JSON only, with all 16 cells, using this shape:
{"cells":[{"cell":"A1","classification":"uncertain","observation":"what is visible","uncertainty":"high"}],"summary":"visual summary","limitations":["A photograph cannot reveal people hidden beneath opaque debris."]}
uncertainty must be low, medium, or high.
"""

REASONING_INSTRUCTIONS = """You prioritize visible sectors for a follow-up look. Your only evidence is the structured visual observations below.
You do not have vibration, audio, radar, thermal, or ranging data.

Rules:
- Recommend further visual inspection of sectors that look debris-covered, obstructed, or like a visible opening.
- Quote or paraphrase the visual observation as evidence.
- Do not claim a person is present.
- Do not invent confidence scores, heat signatures, distances, or sensor readings.
- Return JSON only:
{"priorities":[{"cell":"B2","priority":1,"reason":"why this visible sector should be inspected next","evidence":["the visual observation"],"uncertainty":"what remains unknown","next_action":"what a person should look at next"}],"uncertainties":["limits of this photograph"],"cannot_infer":["buried survivors","vital signs","heat signatures","distances through rubble"]}
Use only cell ids from A1 through D4. priority is an integer starting at 1. Omit cells you would not inspect next.
"""


def analyze_image(image_bytes: bytes, media_type: str, client: NebiusClient | None = None) -> VisionAnalysis:
    client = client or NebiusClient()
    try:
        models = client.list_models()
        chosen = select_vision_model(models, os.getenv("NEBIUS_VISION_MODEL") or None)
        if not accepts_images(chosen):
            raise LookupError(f"{chosen.id} does not accept images")
        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{media_type};base64,{encoded}"
        content = client.chat(
            chosen.id,
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_INSTRUCTIONS},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        )
        payload: VisionPayload = validate_vision(content)
    except (NebiusError, LookupError, ValueError) as exc:
        return VisionAnalysis(model_id="", request_status="failed", error=str(exc), limitations=[PHOTO_LIMITATION])
    cells = [cell.model_copy(update={"source": "model"}) for cell in payload.cells]
    return VisionAnalysis(
        model_id=chosen.id,
        request_status="succeeded",
        summary=payload.summary,
        limitations=payload.limitations,
        cells=cells,
    )


def reason_about(observations: list[dict], client: NebiusClient | None = None, image_bytes: bytes | None = None, media_type: str = "image/jpeg") -> ReasoningResult:
    client = client or NebiusClient()
    try:
        models = client.list_models()
        chosen = select_reasoning_model(models, os.getenv("NEBIUS_REASONING_MODEL") or None)
        user_content: list[dict] | str
        image_input_used = False
        text = REASONING_INSTRUCTIONS + "\n\nVisual observations JSON:\n" + _observations_text(observations)
        if image_bytes is not None and accepts_images(chosen):
            encoded = base64.b64encode(image_bytes).decode("ascii")
            user_content = [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{encoded}"}},
            ]
            image_input_used = True
        else:
            user_content = text
        content = client.chat(chosen.id, [{"role": "user", "content": user_content}], max_tokens=1200)
        payload = validate_reasoning(content)
    except (NebiusError, LookupError, ValueError) as exc:
        return ReasoningResult(request_status="failed", error=str(exc), image_input_used=False)
    return ReasoningResult(
        model_id=chosen.id,
        image_input_used=image_input_used,
        request_status="succeeded",
        priorities=payload.priorities,
        uncertainties=payload.uncertainties,
        cannot_infer=payload.cannot_infer,
    )


def _observations_text(observations: list[dict]) -> str:
    import json

    return json.dumps(observations, indent=2)
