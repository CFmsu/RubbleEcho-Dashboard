import json

ALLOWED_RADAR_KEYS = {
    "human_presence",
    "distance_m",
    "breath_rate_bpm",
    "heart_rate_bpm",
    "total_phase",
    "breath_phase",
    "heart_phase",
    "target_xy_m",
    "firmware",
    "stability",
    "stale",
    "spatial_coordinates_supported",
    "breath_retained",
    "heart_retained",
    "captured_at_utc",
    "valid",
}


def parse_radar_line(line: str) -> tuple[dict | None, str | None]:
    text = line.strip()
    if text.startswith("RADAR "):
        text = text[6:].strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None, "malformed"
    return parse_radar_object(payload)


def parse_radar_object(payload: object) -> tuple[dict | None, str | None]:
    if not isinstance(payload, dict):
        return None, "malformed"
    unknown = set(payload) - ALLOWED_RADAR_KEYS
    if unknown:
        return None, "unknown_keys:" + ",".join(sorted(unknown))

    presence = payload.get("human_presence")
    if presence is not None and not isinstance(presence, bool):
        return None, "malformed_presence"

    stability = payload.get("stability")
    stale = bool(payload.get("stale", False))
    notes: list[str] = []
    breath = payload.get("breath_rate_bpm")
    heart = payload.get("heart_rate_bpm")
    breath_phase = payload.get("breath_phase")
    heart_phase = payload.get("heart_phase")

    if stability != "stationary" or stale:
        if breath is not None:
            notes.append("breath_suppressed_until_stable" if not stale else "stale_breath_suppressed")
        if heart is not None:
            notes.append("heart_suppressed_until_stable" if not stale else "stale_heart_suppressed")
        breath = None
        heart = None
        breath_phase = None
        heart_phase = None
    if payload.get("breath_retained"):
        breath = None
        notes.append("breath_retained_value_suppressed")
    if payload.get("heart_retained"):
        heart = None
        notes.append("heart_retained_value_suppressed")

    target = None
    spatial_used = False
    if payload.get("target_xy_m") is not None:
        if payload.get("spatial_coordinates_supported") is True:
            raw_target = payload["target_xy_m"]
            if (
                isinstance(raw_target, list)
                and len(raw_target) == 2
                and all(isinstance(value, (int, float)) for value in raw_target)
            ):
                target = [float(raw_target[0]), float(raw_target[1])]
                spatial_used = True
            else:
                return None, "malformed_target_xy"
        else:
            notes.append("xy_ignored_firmware_unverified")

    valid = bool(payload.get("valid", True)) and not stale
    return {
        "human_presence": presence,
        "distance_m": payload.get("distance_m"),
        "breath_rate_bpm": breath,
        "heart_rate_bpm": heart,
        "total_phase": payload.get("total_phase") if not stale else None,
        "breath_phase": breath_phase,
        "heart_phase": heart_phase,
        "target_xy_m": target,
        "firmware": payload.get("firmware"),
        "stability": stability,
        "stale": stale,
        "valid": valid,
        "spatial_coordinates_used": spatial_used,
        "notes": notes,
        "captured_at_utc": payload.get("captured_at_utc"),
        "source_mode": "unavailable",
    }, None
