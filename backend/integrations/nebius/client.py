"""Nebius Token Factory client. OpenAI-compatible chat completions.

Base URL defaults to https://api.tokenfactory.nebius.com/v1.
Credentials come from NEBIUS_API_KEY. This module never invents a completion.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from field.models_catalog import ModelInfo, parse_model_record

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1"


class NebiusError(RuntimeError):
    pass


class NebiusClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("NEBIUS_API_KEY", "")
        self.base_url = (base_url or os.getenv("NEBIUS_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip())

    def _client(self) -> httpx.Client:
        if not self.configured:
            raise NebiusError("NEBIUS_API_KEY is not set. Manual labels still work. No inference was sent.")
        return httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=httpx.Timeout(120.0, connect=15.0),
            transport=self._transport,
        )

    def list_models(self) -> list[ModelInfo]:
        with self._client() as client:
            response = client.get("/models")
        _raise_for_status(response)
        body = response.json()
        records = body.get("data", body if isinstance(body, list) else [])
        if not isinstance(records, list):
            raise NebiusError("Nebius /models response did not contain a model list")
        return [parse_model_record(item) for item in records if isinstance(item, dict)]

    def chat(self, model: str, messages: list[dict[str, Any]], *, max_tokens: int = 1800) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        with self._client() as client:
            response = client.post("/chat/completions", json=payload)
            if response.status_code == 400:
                payload.pop("response_format", None)
                response = client.post("/chat/completions", json=payload)
        _raise_for_status(response)
        body = response.json()
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise NebiusError("Nebius response did not include a message") from exc
        if isinstance(content, list):
            texts = [part.get("text", "") for part in content if isinstance(part, dict)]
            content = "\n".join(texts)
        if not isinstance(content, str) or not content.strip():
            raise NebiusError("Nebius response message was empty")
        return content


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    detail = response.text.strip().replace("\n", " ")
    if len(detail) > 400:
        detail = detail[:400] + "…"
    raise NebiusError(f"Nebius HTTP {response.status_code}: {detail or response.reason_phrase}")
