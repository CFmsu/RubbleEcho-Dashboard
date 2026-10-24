"""Report Nebius configuration. A live call happens only with --live and a real key."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.ai.nebius_client import ai_status, reason_live


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    status = ai_status()
    print(f"status={status['status']}")
    print(f"model_id={status['model_id']}")
    print(f"nvidia_online={status['nvidia_online']}")
    if not args.live:
        print("live call skipped. Pass --live only when NEBIUS_API_KEY and NEBIUS_MODEL_ID are set.")
        return 0
    if status["status"] == "NOT_CONFIGURED":
        print("NOT_CONFIGURED")
        return 2
    result = reason_live([], set(), {"A_FAR", "A_NEAR", "B_FAR", "B_NEAR", "C_FAR", "C_NEAR"})
    print(f"live_ok={result.get('ok')}")
    print(f"kind={result.get('kind')}")
    if result.get("ok"):
        payload = result["result"]
        print(f"provider={payload.get('provider')}")
        print(f"model_id={payload.get('model_id')}")
        print(f"latency_ms={payload.get('latency_ms')}")
        print(f"validation_status={payload.get('validation_status')}")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
