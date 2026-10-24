from typing import Protocol


class SampleParser(Protocol):
    def parse(self, payload: dict) -> dict | None:
        """Return a normalized sample, or None when the payload is not usable."""


def next_backoff_seconds(attempt: int) -> float:
    """Bounded reconnect delay. Attempt 0 waits 0.5 s and the delay caps at 10 s."""
    if attempt < 0:
        attempt = 0
    return min(0.5 * (2**attempt), 10.0)
