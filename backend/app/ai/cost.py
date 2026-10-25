"""Token ledger for Token Factory calls.

Rates are the public Nebius catalog prices in USD per one million tokens.
The sum is a catalog estimate, not an invoice.
"""

CATALOG_USD_PER_MILLION = {
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": (0.06, 0.24),
    "nvidia/Nemotron-3.5-Super-VL": (0.30, 0.90),
}


def blank_usage() -> dict:
    return {
        "calls": [],
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_usd": 0.0,
    }


def estimate_usd(model_id: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    rate = CATALOG_USD_PER_MILLION.get(model_id)
    if rate is None:
        return None
    return (prompt_tokens / 1_000_000) * rate[0] + (completion_tokens / 1_000_000) * rate[1]


def note_usage(stage: str, model_id: str, usage: dict | None) -> None:
    from app.state import get_state

    state = get_state()
    ledger = state.ai_usage if isinstance(getattr(state, "ai_usage", None), dict) else blank_usage()
    prompt = _count(None if usage is None else usage.get("prompt_tokens"))
    completion = _count(None if usage is None else usage.get("completion_tokens"))
    total = _count(None if usage is None else usage.get("total_tokens"))
    if total == 0:
        total = prompt + completion
    priced = estimate_usd(model_id, prompt, completion)
    ledger["calls"].append(
        {
            "stage": stage,
            "model_id": model_id,
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
            "estimated_usd": None if priced is None else round(priced, 6),
        }
    )
    ledger["prompt_tokens"] += prompt
    ledger["completion_tokens"] += completion
    ledger["total_tokens"] += total
    if priced is not None:
        ledger["estimated_usd"] = round(float(ledger.get("estimated_usd") or 0) + priced, 6)
    state.ai_usage = ledger


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, int(value))
