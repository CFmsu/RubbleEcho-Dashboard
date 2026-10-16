"""Strict schemas for visual findings and Nemotron recommendations.

A photograph cannot show people hidden under opaque debris. These models
reject extra fields so a response cannot smuggle survivor, vital-sign,
heat, or distance claims into the stored record.
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from field.grid import CELL_IDS

Classification = Literal[
    "debris_covered",
    "obstructed",
    "clear_surface",
    "possible_opening",
    "uncertain",
]
Uncertainty = Literal["low", "medium", "high"]
CellSource = Literal["unanalyzed", "model", "manual_correction"]

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)
_FORBIDDEN_CLAIM = re.compile(
    r"\b(survivor detected|buried (person|survivor)|vital signs detected|"
    r"heartbeat detected|heat signature|body beneath|person trapped)\b",
    re.IGNORECASE,
)
PHOTO_LIMITATION = "A photograph cannot reveal people hidden beneath opaque debris."


class GridCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell: str
    classification: Classification
    observation: str = ""
    uncertainty: Uncertainty = "high"
    source: CellSource = "unanalyzed"

    @field_validator("cell")
    @classmethod
    def known_cell(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in CELL_IDS:
            raise ValueError(f"cell must be one of {', '.join(CELL_IDS)}")
        return normalized

    @field_validator("observation")
    @classmethod
    def no_hidden_person_claim(cls, value: str) -> str:
        if _FORBIDDEN_CLAIM.search(value):
            raise ValueError("observation infers a hidden person or an unmeasured signal")
        return value.strip()


class VisionPayload(BaseModel):
    """What the vision model is allowed to return. Provenance is added by the server."""

    model_config = ConfigDict(extra="forbid")

    cells: list[GridCell]
    summary: str
    limitations: list[str] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def summary_is_visual(cls, value: str) -> str:
        if _FORBIDDEN_CLAIM.search(value):
            raise ValueError("summary infers a hidden person or an unmeasured signal")
        return value.strip()

    @field_validator("cells")
    @classmethod
    def exact_grid(cls, cells: list[GridCell]) -> list[GridCell]:
        found = [cell.cell for cell in cells]
        if len(found) != len(set(found)) or set(found) != set(CELL_IDS):
            raise ValueError("cells must contain each of A1–D4 exactly once")
        order = {cell_id: index for index, cell_id in enumerate(CELL_IDS)}
        return sorted(cells, key=lambda cell: order[cell.cell])


class VisionAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    request_status: Literal["succeeded", "failed", "not_run"]
    error: str | None = None
    summary: str = ""
    limitations: list[str] = Field(default_factory=list)
    cells: list[GridCell] = Field(default_factory=list)


class SectorRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell: str
    priority: int = Field(ge=1, le=16)
    reason: str
    evidence: list[str]
    uncertainty: str
    next_action: str

    @field_validator("cell")
    @classmethod
    def known_cell(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in CELL_IDS:
            raise ValueError(f"cell must be one of {', '.join(CELL_IDS)}")
        return normalized

    @field_validator("reason", "uncertainty", "next_action")
    @classmethod
    def grounded_text(cls, value: str) -> str:
        if _FORBIDDEN_CLAIM.search(value):
            raise ValueError("recommendation infers a hidden person or an unmeasured signal")
        return value.strip()

    @field_validator("evidence")
    @classmethod
    def grounded_evidence(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            if _FORBIDDEN_CLAIM.search(value):
                raise ValueError("evidence infers a hidden person or an unmeasured signal")
            text = value.strip()
            if text:
                cleaned.append(text)
        if not cleaned:
            raise ValueError("each recommendation needs visual evidence")
        return cleaned


class ReasoningPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priorities: list[SectorRecommendation]
    uncertainties: list[str]
    cannot_infer: list[str]

    @field_validator("priorities")
    @classmethod
    def priorities_are_real_cells(cls, values: list[SectorRecommendation]) -> list[SectorRecommendation]:
        cells = [item.cell for item in values]
        if len(cells) != len(set(cells)):
            raise ValueError("priorities repeat a cell")
        return values


class ReasoningResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str | None = None
    image_input_used: bool = False
    request_status: Literal["succeeded", "failed", "not_run"]
    error: str | None = None
    priorities: list[SectorRecommendation] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    cannot_infer: list[str] = Field(default_factory=list)


def blank_cells() -> list[GridCell]:
    return [
        GridCell(cell=cell_id, classification="uncertain", observation="", uncertainty="high", source="unanalyzed")
        for cell_id in CELL_IDS
    ]


def parse_model_json(text: str) -> dict:
    cleaned = _FENCE.sub("", text.strip())
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("model response did not contain a JSON object")
    try:
        payload = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("model response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("model response JSON must be an object")
    return payload


def validate_vision(text: str) -> VisionPayload:
    payload = VisionPayload.model_validate(parse_model_json(text))
    limitations = list(payload.limitations)
    if PHOTO_LIMITATION not in limitations:
        limitations.append(PHOTO_LIMITATION)
    return payload.model_copy(update={"limitations": limitations})


def validate_reasoning(text: str) -> ReasoningPayload:
    payload = ReasoningPayload.model_validate(parse_model_json(text))
    required = [
        "buried survivors",
        "vital signs",
        "heat signatures",
        "distances through rubble",
    ]
    cannot = list(payload.cannot_infer)
    for item in required:
        if item not in cannot:
            cannot.append(item)
    return payload.model_copy(update={"cannot_infer": cannot})
