from datetime import datetime, timedelta, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fixture_time(at_ms: int) -> str:
    base = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    stamp = base + timedelta(milliseconds=at_ms)
    return stamp.isoformat().replace("+00:00", "Z")
