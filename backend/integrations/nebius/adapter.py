"""Nebius Token Factory text completion used by the field pipeline."""

from __future__ import annotations

from integrations.nebius.client import NebiusClient, NebiusError


class NebiusInferenceAdapter:
    def __init__(self, client: NebiusClient | None = None) -> None:
        self.client = client or NebiusClient()

    def complete(self, prompt: str) -> str:
        if not self.client.configured:
            raise NotImplementedError(
                "Nebius inference is not enabled. Set NEBIUS_API_KEY. The simulated mission stays on the simulated provider."
            )
        try:
            models = self.client.list_models()
        except NebiusError as exc:
            raise NotImplementedError(str(exc)) from exc
        from field.models_catalog import select_reasoning_model

        try:
            chosen = select_reasoning_model(models, None)
        except LookupError as exc:
            raise NotImplementedError(str(exc)) from exc
        try:
            return self.client.chat(chosen.id, [{"role": "user", "content": prompt}])
        except NebiusError as exc:
            raise NotImplementedError(str(exc)) from exc
