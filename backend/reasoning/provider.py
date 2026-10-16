"""Reasoning providers. V1 is deterministic and template-based."""

from __future__ import annotations

from models.mission import SearchDecision
from models.sensors import RawObservation
from reasoning.sensor_fusion import fuse


class ReasoningProvider:
    name = "BASE"

    def decide_next_action(
        self,
        observation: RawObservation,
        target_x: float | None,
        target_y: float | None,
        reason: str,
    ) -> SearchDecision:
        raise NotImplementedError


class SimulatedReasoningProvider(ReasoningProvider):
    name = "SIMULATED"

    def decide_next_action(
        self,
        observation: RawObservation,
        target_x: float | None,
        target_y: float | None,
        reason: str,
    ) -> SearchDecision:
        fused = fuse(observation)
        observation_text = _describe(observation)
        if target_x is None or target_y is None:
            decision = "Hold and reassess the belief map."
        else:
            decision = f"Probe location ({target_x:.1f}, {target_y:.1f})"
        return SearchDecision(
            observation=observation_text,
            decision=decision,
            reason=reason,
            confidence=fused.combined,
            target_x=target_x,
            target_y=target_y,
            provider=self.name,
        )


def _describe(observation: RawObservation) -> str:
    parts: list[str] = []
    if observation.vibration >= 0.55:
        parts.append("Strong vibration reflection detected.")
    elif observation.vibration >= 0.32:
        parts.append("Weak vibration anomaly detected.")
    else:
        parts.append("Vibration remained near the environmental baseline.")

    if observation.audio_state == "CONFIRMED_RESPONSE":
        parts.append("Repeated acoustic taps detected after the knock.")
    elif observation.audio_state == "POSSIBLE_TAP":
        parts.append("A possible human tap was detected after the knock.")
    elif observation.audio_state == "WEAK_RESPONSE":
        parts.append("A weak acoustic event was detected during the listening window.")
    else:
        parts.append("No human response detected in the listening window.")

    if observation.cavity >= 0.5:
        parts.append("Cavity likelihood increased near the contact point.")
    return " ".join(parts)
