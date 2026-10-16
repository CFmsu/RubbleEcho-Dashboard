"""NVIDIA Nemotron reasoning, hosted through Nebius Token Factory.

The simulated mission loop does not call this adapter. Live reasoning runs
from the field observation pipeline, and only on visual findings that came
from a photograph or a manual label. Nemotron is not sent an image unless
the selected model catalog entry lists image input.
"""

from __future__ import annotations

from field.inference import reason_about
from integrations.nebius.client import NebiusClient


class NvidiaReasoningAdapter:
    def __init__(self, client: NebiusClient | None = None) -> None:
        self.client = client or NebiusClient()

    def analyze(self, observation: dict) -> dict:
        result = reason_about([observation], client=self.client)
        if result.request_status != "succeeded":
            raise NotImplementedError(result.error or "Nemotron reasoning did not return a result.")
        return result.model_dump()
