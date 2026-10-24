import json
import time

from app.ai.prompts import build_messages
from app.ai.validators import validate_reasoning
from app.config.settings import AI_TIMEOUT_S, nebius_base_url, nebius_key, nebius_model


def ai_status() -> dict:
    key = nebius_key()
    model = nebius_model()
    status = {
        "provider": "nebius_token_factory",
        "model_id": model or None,
        "nvidia_online": False,
        "live_call": False,
        "base_url_host": "api.tokenfactory.nebius.com",
    }
    if not key or not model:
        status["status"] = "NOT_CONFIGURED"
        status["message"] = (
            "Set NEBIUS_API_KEY and NEBIUS_MODEL_ID. "
            "Choose the model id from the Token Factory catalog, and only if it is an NVIDIA model."
        )
        return status
    status["status"] = "CONFIGURED_UNVERIFIED"
    status["message"] = (
        "A key and model id are set. This process has not recorded a successful live catalog check."
    )
    return status


def select_nvidia_model(model_ids: list[str], preferred: str | None = None) -> dict:
    nvidia = [model_id for model_id in model_ids if _is_nvidia(model_id)]
    if preferred:
        if preferred not in model_ids:
            return {"model_id": None, "reason": "preferred_model_not_in_catalog"}
        if not _is_nvidia(preferred):
            return {"model_id": None, "reason": "preferred_model_is_not_nvidia"}
        return {"model_id": preferred, "reason": "preferred_nvidia_model"}
    if not nvidia:
        return {"model_id": None, "reason": "no_nvidia_model_in_catalog"}
    nemotron = [model_id for model_id in nvidia if "nemotron" in model_id.lower()]
    chosen = nemotron[0] if nemotron else nvidia[0]
    return {"model_id": chosen, "reason": "catalog_nvidia_model"}


def interpret_model_text(
    payload_text: str,
    known_event_ids: set[str],
    known_points: set[str],
    model_id: str,
    latency_ms: float,
    live_call: bool,
) -> tuple[dict | None, str | None]:
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return None, "invalid_json"
    result, error = validate_reasoning(payload, known_event_ids, known_points)
    if error or result is None:
        return None, error or "invalid"
    result.update(
        {
            "provider": "nebius_token_factory",
            "model_id": model_id,
            "latency_ms": latency_ms,
            "nvidia_online": bool(live_call),
            "live_call": bool(live_call),
            "validation_status": "valid",
        }
    )
    return result, None


def reason_live(
    evidence: list[dict],
    known_event_ids: set[str],
    known_points: set[str],
) -> dict:
    """Call Token Factory. Tests should not use this; they call interpret_model_text."""
    status = ai_status()
    if status["status"] == "NOT_CONFIGURED":
        return {"ok": False, "kind": "not_configured"}
    model_id = nebius_model()
    try:
        from openai import OpenAI
    except ImportError:
        return {"ok": False, "kind": "openai_sdk_not_installed"}

    started = time.perf_counter()
    try:
        client = OpenAI(
            base_url=nebius_base_url(),
            api_key=nebius_key(),
            timeout=AI_TIMEOUT_S,
        )
        response = client.chat.completions.create(
            model=model_id,
            messages=build_messages(evidence, sorted(known_points)),
            temperature=0,
        )
    except TimeoutError:
        return {"ok": False, "kind": "timeout"}
    except Exception as exc:
        kind = _classify_exception(exc)
        return {"ok": False, "kind": kind}

    latency_ms = (time.perf_counter() - started) * 1000
    content = ""
    try:
        content = response.choices[0].message.content or ""
    except (AttributeError, IndexError):
        return {"ok": False, "kind": "empty_response"}
    usage = None
    if getattr(response, "usage", None) is not None:
        usage = {
            "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
            "completion_tokens": getattr(response.usage, "completion_tokens", None),
            "total_tokens": getattr(response.usage, "total_tokens", None),
        }
    result, error = interpret_model_text(
        content,
        known_event_ids,
        known_points,
        model_id,
        latency_ms,
        live_call=True,
    )
    if error or result is None:
        return {"ok": False, "kind": error or "invalid_json"}
    result["usage"] = usage
    return {"ok": True, "result": result}


def _is_nvidia(model_id: str) -> bool:
    text = model_id.lower()
    return "nvidia" in text or "nemotron" in text


def _classify_exception(exc: Exception) -> str:
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return "http_429"
    if status_code == 500:
        return "http_500"
    name = exc.__class__.__name__.lower()
    if "timeout" in name:
        return "timeout"
    return "provider_error"
