"""Choose Nebius models without assuming Nemotron can see images."""

from __future__ import annotations

import re
from dataclasses import dataclass

_VISION_ID = re.compile(
    r"(qwen[\d.]*[-_]?vl|qwen\d+-vl|llava|pixtral|internvl|molmo|phi-3-vision|phi-4-.*vision|minicpm-v|minicpm_v)",
    re.IGNORECASE,
)
_IMAGE_MODALITIES = {"image", "vision"}


@dataclass(frozen=True)
class ModelInfo:
    id: str
    input_modalities: tuple[str, ...] = ()


def parse_model_record(item: dict) -> ModelInfo:
    model_id = str(item.get("id") or item.get("name") or "").strip()
    modalities: list[str] = []
    for key in ("input_modalities", "modalities"):
        raw = item.get(key)
        if isinstance(raw, list):
            modalities.extend(str(value) for value in raw)
    architecture = item.get("architecture")
    if isinstance(architecture, dict):
        raw = architecture.get("input_modalities") or architecture.get("modality")
        if isinstance(raw, list):
            modalities.extend(str(value) for value in raw)
        elif isinstance(raw, str):
            modalities.append(raw)
    return ModelInfo(id=model_id, input_modalities=tuple(part.strip().lower() for part in modalities if str(part).strip()))


def accepts_images(model: ModelInfo) -> bool:
    if not model.id:
        return False
    if any(part in _IMAGE_MODALITIES or "image" in part for part in model.input_modalities):
        return True
    # A Nemotron id is text reasoning unless the catalog explicitly lists image input.
    if "nemotron" in model.id.lower():
        return False
    return _VISION_ID.search(model.id) is not None


def select_vision_model(models: list[ModelInfo], override: str | None) -> ModelInfo:
    by_id = {model.id: model for model in models if model.id}
    if override:
        chosen = by_id.get(override)
        if chosen is None:
            raise LookupError(f"NEBIUS_VISION_MODEL '{override}' is not in the Nebius model catalog")
        if not accepts_images(chosen):
            raise LookupError(
                f"NEBIUS_VISION_MODEL '{override}' is not image-capable. "
                "Refusing to send a photograph to it."
            )
        return chosen
    capable = [model for model in models if accepts_images(model)]
    if not capable:
        raise LookupError(
            "No image-capable model was listed by Nebius. "
            "Set NEBIUS_VISION_MODEL to a vision model id from GET /v1/models."
        )

    def rank(model: ModelInfo) -> tuple[int, str]:
        name = model.id.lower()
        if "qwen" in name and "vl" in name:
            return (0, name)
        if "minicpm-v" in name or "minicpm_v" in name:
            return (1, name)
        if "internvl" in name or "pixtral" in name:
            return (2, name)
        return (3, name)

    return sorted(capable, key=rank)[0]


def select_reasoning_model(models: list[ModelInfo], override: str | None) -> ModelInfo:
    by_id = {model.id: model for model in models if model.id}
    if override:
        chosen = by_id.get(override)
        if chosen is None:
            raise LookupError(f"NEBIUS_REASONING_MODEL '{override}' is not in the Nebius model catalog")
        return chosen
    nemotron = [model for model in models if "nemotron" in model.id.lower()]
    if not nemotron:
        raise LookupError(
            "No NVIDIA Nemotron model was listed by Nebius. "
            "Set NEBIUS_REASONING_MODEL to a Nemotron model id from GET /v1/models."
        )

    def rank(model: ModelInfo) -> tuple[int, str]:
        name = model.id.lower()
        if "lightning" in name:
            return (0, name)
        if "nano" in name and "omni" not in name:
            return (1, name)
        if "super" in name:
            return (2, name)
        if "ultra" in name:
            return (3, name)
        return (4, name)

    return sorted(nemotron, key=rank)[0]
