import base64
import json
import time

from app.ai.cost import note_usage
from app.ai.prompts import build_messages, build_plan_messages, build_scene_messages
from app.ai.validators import _reject_forbidden, validate_reasoning
from app.config.settings import AI_TIMEOUT_S, ai_enabled, nebius_base_url, nebius_key, nebius_model, nebius_vision_model


def ai_status() -> dict:
    key = nebius_key()
    model = nebius_model()
    status = {
        "provider": "nebius_token_factory",
        "model_id": model or None,
        "vision_model_id": nebius_vision_model() or None,
        "nvidia_online": False,
        "live_call": False,
        "base_url_host": "api.tokenfactory.nebius.com",
    }
    if not ai_enabled() or not key or not model:
        status["status"] = "NOT_CONFIGURED"
        status["message"] = "AI is not configured. No Token Factory call has been made."
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
    payload = _load_object(payload_text)
    if payload is None:
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
    search_plan: dict | None = None,
    cells: list[dict] | None = None,
) -> dict:
    """Call Token Factory. Tests should not use this; they call interpret_model_text."""
    model_id = nebius_model()
    reply = _chat(
        model_id,
        build_messages(evidence, sorted(known_points), search_plan, cells),
        max_tokens=4000,
        timeout=45,
    )
    _charge("reason", model_id, reply)
    if not reply.get("ok"):
        return {"ok": False, "kind": reply.get("kind")}
    result, error = interpret_model_text(
        reply["content"],
        known_event_ids,
        known_points,
        model_id,
        reply.get("latency_ms") or 0,
        live_call=True,
    )
    if error or result is None:
        return {"ok": False, "kind": error or "invalid_json"}
    result["usage"] = reply.get("usage")
    return {"ok": True, "result": result}


def plan_live(photo: dict, point_ids: list[str]) -> dict:
    """Ask for a grid boundary and a point order. Returns text for the search planner to validate."""
    model_id = nebius_model()
    reply = _chat(
        model_id,
        build_plan_messages(photo, point_ids),
        max_tokens=2000,
        timeout=45,
    )
    _charge("plan", model_id, reply)
    if not reply.get("ok"):
        return {"ok": False, "kind": reply.get("kind")}
    return {"ok": True, "text": reply["content"], "model_id": model_id, "usage": reply.get("usage")}


def vision_live(image: bytes, mime: str, note: str) -> dict:
    """Describe one stored frame. Returns before any network call when no vision model is set."""
    model_id = nebius_vision_model()
    if not model_id:
        return {"ok": False, "kind": "vision_not_configured"}
    if not _is_nvidia(model_id):
        return {"ok": False, "kind": "vision_model_is_not_nvidia"}
    encoded = base64.b64encode(image).decode("ascii")
    reply = _chat(
        model_id,
        build_scene_messages(note, f"data:{mime};base64,{encoded}"),
        max_tokens=2000,
        timeout=60,
    )
    _charge("vision", model_id, reply)
    if not reply.get("ok"):
        return {"ok": False, "kind": reply.get("kind"), "model_id": model_id}
    scene, error = interpret_scene(reply["content"])
    if error or scene is None:
        return {"ok": False, "kind": error or "invalid_scene", "model_id": model_id}
    return {"ok": True, "scene": scene, "model_id": model_id, "usage": reply.get("usage")}


def interpret_scene(payload_text: str) -> tuple[dict | None, str | None]:
    text = payload_text.strip()
    if not text.startswith("{"):
        text = _json_object(text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(payload, dict):
        return None, "invalid_json_shape"
    try:
        _reject_forbidden(payload)
    except ValueError as exc:
        return None, str(exc)
    scene = payload.get("scene")
    obstacles = payload.get("obstacles")
    open_area = payload.get("open_area")
    if not isinstance(scene, str) or not scene.strip():
        return None, "invalid_scene"
    if not isinstance(obstacles, list) or not all(isinstance(item, str) for item in obstacles):
        return None, "invalid_obstacles"
    if not isinstance(open_area, str) or not open_area.strip():
        return None, "invalid_open_area"
    return {
        "scene": scene.strip(),
        "obstacles": obstacles,
        "open_area": open_area.strip(),
    }, None


def _chat(model_id: str, messages: list, max_tokens: int, timeout: float) -> dict:
    if ai_status()["status"] == "NOT_CONFIGURED" or not model_id:
        return {"ok": False, "kind": "not_configured"}
    try:
        from openai import OpenAI
    except ImportError:
        return {"ok": False, "kind": "openai_sdk_not_installed"}
    started = time.perf_counter()
    try:
        client = OpenAI(base_url=nebius_base_url(), api_key=nebius_key(), timeout=timeout)
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0,
            max_tokens=max_tokens,
        )
    except TimeoutError:
        return {"ok": False, "kind": "timeout"}
    except Exception as exc:
        return {"ok": False, "kind": _classify_exception(exc)}
    try:
        message = response.choices[0].message
        content = message.content or ""
        if not content.strip():
            content = _json_object(getattr(message, "reasoning", None) or "")
    except (AttributeError, IndexError):
        content = ""
    usage = _usage(response)
    latency_ms = (time.perf_counter() - started) * 1000
    if not content.strip():
        return {"ok": False, "kind": "empty_response", "usage": usage, "model_id": model_id, "latency_ms": latency_ms}
    return {"ok": True, "content": content, "usage": usage, "model_id": model_id, "latency_ms": latency_ms}


def _charge(stage: str, model_id: str, reply: dict) -> None:
    usage = reply.get("usage")
    if isinstance(usage, dict):
        note_usage(stage, reply.get("model_id") or model_id, usage)


def _usage(response: object) -> dict | None:
    raw = getattr(response, "usage", None)
    if raw is None:
        return None
    return {
        "prompt_tokens": getattr(raw, "prompt_tokens", None),
        "completion_tokens": getattr(raw, "completion_tokens", None),
        "total_tokens": getattr(raw, "total_tokens", None),
    }


def healthcheck() -> dict:
    """Catalog check. Returns before any network call when AI is not configured."""
    status = ai_status()
    if status["status"] == "NOT_CONFIGURED":
        return {
            "ok": False,
            "status": "NOT_CONFIGURED",
            "nvidia_online": False,
            "live_call": False,
            "model_id": status["model_id"],
        }
    model_id = nebius_model()
    try:
        from openai import OpenAI
    except ImportError:
        return {
            "ok": False,
            "status": "ERROR",
            "kind": "openai_sdk_not_installed",
            "nvidia_online": False,
            "live_call": False,
            "model_id": model_id,
        }
    started = time.perf_counter()
    try:
        client = OpenAI(base_url=nebius_base_url(), api_key=nebius_key(), timeout=AI_TIMEOUT_S)
        listing = client.models.list()
        model_ids = [item.id for item in getattr(listing, "data", [])]
    except Exception as exc:
        return {
            "ok": False,
            "status": "ERROR",
            "kind": _classify_exception(exc),
            "nvidia_online": False,
            "live_call": False,
            "model_id": model_id,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        }
    chosen = select_nvidia_model(model_ids, preferred=model_id)
    ok = chosen["model_id"] == model_id
    return {
        "ok": ok,
        "status": "ONLINE" if ok else "ERROR",
        "kind": chosen["reason"],
        "nvidia_online": ok,
        "live_call": True,
        "model_id": model_id,
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def _load_object(text: str) -> dict | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        extracted = _json_object(text)
        if not extracted:
            return None
        try:
            payload = json.loads(extracted)
        except json.JSONDecodeError:
            return None
    if not isinstance(payload, dict):
        return None
    return payload


def _json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return ""
    return text[start : end + 1]


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
