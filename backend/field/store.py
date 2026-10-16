"""Save iPhone photographs and their analyses on disk.

Mission state stays in memory. Field observations are files under the data
directory so a real photo is not mixed into the simulated telemetry snapshot.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from field.schema import GridCell, ReasoningResult, VisionAnalysis, blank_cells

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/heic": ".heic",
    "image/heif": ".heif",
}


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    filename: str
    media_type: str
    created_at: str
    width: int
    height: int
    cells: list[GridCell]
    analysis: VisionAnalysis
    reasoning: ReasoningResult


class FieldStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._root = _default_root()
        self._observations: dict[str, Observation] = {}
        self._mode = "demo"
        self.load()

    def configure(self, root: Path) -> None:
        with self._lock:
            self._root = root
            self._observations = {}
            self._mode = "demo"
            self._root.mkdir(parents=True, exist_ok=True)
            self._read_from_disk()

    def reset(self) -> None:
        with self._lock:
            self._observations = {}
            self._mode = "demo"
            folder = self._root / "observations"
            if folder.exists():
                for path in folder.glob("*"):
                    if path.is_dir():
                        for child in path.iterdir():
                            if child.is_file():
                                child.unlink()
                        path.rmdir()
            mode_path = self._root / "mode.json"
            if mode_path.exists():
                mode_path.unlink()

    def load(self) -> None:
        with self._lock:
            self._root.mkdir(parents=True, exist_ok=True)
            self._read_from_disk()

    def _read_from_disk(self) -> None:
        folder = self._root / "observations"
        folder.mkdir(parents=True, exist_ok=True)
        loaded: dict[str, Observation] = {}
        for meta in folder.glob("*/meta.json"):
            try:
                loaded[meta.parent.name] = Observation.model_validate_json(meta.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
        self._observations = loaded
        mode_path = self._root / "mode.json"
        if mode_path.exists():
            try:
                value = json.loads(mode_path.read_text(encoding="utf-8")).get("operating_mode")
            except (OSError, json.JSONDecodeError):
                value = None
            if value in {"demo", "real"}:
                self._mode = value

    @property
    def root(self) -> Path:
        return self._root

    def operating_mode(self) -> str:
        with self._lock:
            return self._mode

    def set_operating_mode(self, mode: str) -> str:
        if mode not in {"demo", "real"}:
            raise ValueError("operating_mode must be demo or real")
        with self._lock:
            self._mode = mode
            self._root.mkdir(parents=True, exist_ok=True)
            (self._root / "mode.json").write_text(json.dumps({"operating_mode": mode}), encoding="utf-8")
            return self._mode

    def list_observations(self) -> list[Observation]:
        with self._lock:
            return sorted(self._observations.values(), key=lambda item: item.created_at, reverse=True)

    def get(self, observation_id: str) -> Observation | None:
        with self._lock:
            return self._observations.get(observation_id)

    def image_path(self, observation_id: str) -> Path | None:
        observation = self.get(observation_id)
        if observation is None:
            return None
        path = self._root / "observations" / observation.id / "display.jpg"
        if path.exists():
            return path
        return None

    def create(
        self,
        *,
        filename: str,
        media_type: str,
        original: bytes,
        display_jpeg: bytes,
        width: int,
        height: int,
        source: str,
    ) -> Observation:
        observation_id = uuid.uuid4().hex
        extension = ALLOWED_TYPES.get(media_type, ".bin")
        observation = Observation(
            id=observation_id,
            source=source,
            filename=filename,
            media_type=media_type,
            created_at=datetime.now(timezone.utc).isoformat(),
            width=width,
            height=height,
            cells=blank_cells(),
            analysis=VisionAnalysis(model_id="", request_status="not_run"),
            reasoning=ReasoningResult(request_status="not_run"),
        )
        folder = self._root / "observations" / observation_id
        with self._lock:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"original{extension}").write_bytes(original)
            (folder / "display.jpg").write_bytes(display_jpeg)
            self._write(observation)
        return observation

    def save_analysis(self, observation_id: str, analysis: VisionAnalysis) -> Observation:
        with self._lock:
            current = self._require(observation_id)
            cells = list(current.cells)
            if analysis.request_status == "succeeded":
                manual = {cell.cell for cell in cells if cell.source == "manual_correction"}
                replacement = {cell.cell: cell for cell in analysis.cells}
                cells = [cell if cell.cell in manual else replacement[cell.cell] for cell in cells]
            updated = current.model_copy(update={"analysis": analysis, "cells": cells})
            self._write(updated)
            return updated

    def save_reasoning(self, observation_id: str, reasoning: ReasoningResult) -> Observation:
        with self._lock:
            current = self._require(observation_id)
            updated = current.model_copy(update={"reasoning": reasoning})
            self._write(updated)
            return updated

    def correct_cell(self, observation_id: str, cell: GridCell) -> Observation:
        with self._lock:
            current = self._require(observation_id)
            corrected = cell.model_copy(update={"source": "manual_correction"})
            cells = [corrected if item.cell == corrected.cell else item for item in current.cells]
            updated = current.model_copy(update={"cells": cells})
            self._write(updated)
            return updated

    def _require(self, observation_id: str) -> Observation:
        current = self._observations.get(observation_id)
        if current is None:
            raise KeyError(observation_id)
        return current

    def _write(self, observation: Observation) -> None:
        folder = self._root / "observations" / observation.id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "meta.json").write_text(observation.model_dump_json(indent=2), encoding="utf-8")
        self._observations[observation.id] = observation


def _default_root() -> Path:
    override = os.getenv("RUBBLEECHO_DATA_DIR")
    if override:
        return Path(override) / "field"
    return Path(__file__).resolve().parents[1] / "data" / "field"


store = FieldStore()
