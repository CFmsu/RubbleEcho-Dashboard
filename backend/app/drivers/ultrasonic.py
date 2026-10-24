def parse_ultrasonic(payload: dict) -> dict:
    """Normalize an obstacle range. This is not a rubble-depth or survivor-depth measurement."""
    distance = payload.get("distance_cm")
    timeout = bool(payload.get("echo_timeout", False))
    direction = payload.get("direction") or "forward"
    quality = payload.get("quality") or "unverified_driver"
    notes: list[str] = []

    if timeout or distance is None:
        return {
            "distance_cm": None,
            "echo_timeout": True,
            "direction": direction,
            "quality": "timeout",
            "notes": ["missing_echo"],
            "source_mode": "unavailable",
        }

    if not isinstance(distance, (int, float)) or isinstance(distance, bool):
        return {
            "distance_cm": None,
            "echo_timeout": False,
            "direction": direction,
            "quality": "malformed",
            "notes": ["malformed_distance"],
            "source_mode": "unavailable",
        }

    # Datasheet-style clamp for an HC-SR04. Confirm the installed module before treating
    # these edges as a calibrated instrument range.
    if distance < 2 or distance > 400:
        notes.append("out_of_range_clamped")
        return {
            "distance_cm": None,
            "echo_timeout": False,
            "direction": direction,
            "quality": "out_of_range",
            "notes": notes,
            "source_mode": "unavailable",
        }

    return {
        "distance_cm": float(distance),
        "echo_timeout": False,
        "direction": direction,
        "quality": quality,
        "notes": notes,
        "source_mode": "unavailable",
    }
