import json

ALLOWED_RADAR_KEYS = {
    "human_presence",
    "distance_m",
    "breath_rate_bpm",
    "heart_rate_bpm",
    "total_phase",
    "breath_phase",
    "heart_phase",
    "num_targets",
    "illuminance_lx",
    "distance_cm",
    "distance_reported",
    "distance_unit",
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

    # The stock ESPHome kit does not send stability. Drop rates only when a
    # line explicitly says the target is moving, or the sample is stale.
    if stale or (stability is not None and stability != "stationary"):
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
    distance_m, distance_reported, distance_unit = _distance_fields(payload)
    return {
        "human_presence": presence,
        "distance_m": distance_m,
        "distance_reported": distance_reported,
        "distance_unit": distance_unit,
        "breath_rate_bpm": breath,
        "heart_rate_bpm": heart,
        "num_targets": payload.get("num_targets"),
        "illuminance_lx": payload.get("illuminance_lx"),
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


def _distance_fields(payload: dict) -> tuple[float | None, float | None, str | None]:
    if payload.get("distance_m") is not None:
        meters = float(payload["distance_m"])
        return meters, meters, "m"
    if payload.get("distance_cm") is not None:
        centimeters = float(payload["distance_cm"])
        return centimeters / 100.0, centimeters, "cm"
    if payload.get("distance_reported") is not None:
        return interpret_distance(float(payload["distance_reported"]), payload.get("distance_unit"))
    return None, None, None


def interpret_distance(raw: float, unit: str | None) -> tuple[float, float, str]:
    """ESPHome publishes the module float as-is. Values above 15 are centimeters."""
    label = (unit or "").strip().lower()
    if label in {"cm", "centimeter", "centimeters"}:
        return raw / 100.0, raw, "cm"
    if label in {"m", "meter", "meters"}:
        return raw, raw, "m"
    if raw > 15.0:
        return raw / 100.0, raw, "assumed_cm"
    return raw, raw, "assumed_m"


def blank_reading() -> dict:
    return {
        "human_presence": None,
        "breath_rate_bpm": None,
        "heart_rate_bpm": None,
        "distance_reported": None,
        "distance_unit": None,
        "num_targets": None,
        "illuminance_lx": None,
        "total_phase": None,
        "breath_phase": None,
        "heart_phase": None,
    }


def apply_esphome_line(reading: dict, line: str) -> bool:
    """Fold one ESPHome log line into a reading. Returns True when a field changes."""
    import re

    match = re.search(
        r"'(?P<name>[^']+)'\s*:\s*Sending state\s+(?P<value>ON|OFF|-?\d+(?:\.\d+)?)",
        line,
        flags=re.IGNORECASE,
    )
    if match is None:
        return False
    name = match.group("name").lower()
    raw = match.group("value")
    if "person" in name or "has_target" in name or "presence" in name:
        reading["human_presence"] = raw.upper() == "ON" or raw not in {"OFF", "0", "0.0"}
        return True
    number = float(raw) if raw.upper() not in {"ON", "OFF"} else None
    if number is None:
        return False
    if "breath" in name or "respirat" in name:
        reading["breath_rate_bpm"] = number
    elif "heart" in name:
        reading["heart_rate_bpm"] = number
    elif "distance" in name:
        unit = None
        if re.search(r"\bcm\b", line, flags=re.IGNORECASE):
            unit = "cm"
        elif re.search(r"\bm\b", line):
            unit = "m"
        reading["distance_reported"] = number
        reading["distance_unit"] = unit
    elif "target" in name:
        reading["num_targets"] = int(number)
    elif "illuminance" in name or "lux" in name or "light" in name:
        reading["illuminance_lx"] = number
    else:
        return False
    return True


def reading_to_observation(reading: dict, source_mode: str, firmware: str) -> dict:
    payload = {
        "human_presence": reading.get("human_presence"),
        "breath_rate_bpm": reading.get("breath_rate_bpm"),
        "heart_rate_bpm": reading.get("heart_rate_bpm"),
        "num_targets": reading.get("num_targets"),
        "illuminance_lx": reading.get("illuminance_lx"),
        "total_phase": reading.get("total_phase"),
        "breath_phase": reading.get("breath_phase"),
        "heart_phase": reading.get("heart_phase"),
        "distance_reported": reading.get("distance_reported"),
        "distance_unit": reading.get("distance_unit"),
        "stability": "stationary" if reading.get("human_presence") else None,
        "stale": False,
        "valid": True,
        "firmware": firmware,
        "spatial_coordinates_supported": False,
    }
    if reading.get("distance_m") is not None:
        payload["distance_m"] = reading["distance_m"]
        payload.pop("distance_reported", None)
    observation, error = parse_radar_object(payload)
    if observation is None:
        raise ValueError(error or "radar reading rejected")
    observation["source_mode"] = source_mode
    observation["notes"] = list(observation["notes"]) + [
        "MR60BHA2 reports presence, breath, heart, distance, and target count",
        "this module does not report a bearing",
        "illuminance is the kit light sensor, not the radar",
    ]
    return observation


def parse_binary_frames(buffer: bytearray) -> list[dict]:
    """Pull complete MR60BHA2 UART frames out of a byte buffer.

    Frame layout used by ESPHome's seeed_mr60bha2 parser:
    01 | id_hi id_lo | len_hi len_lo | type_hi type_lo | head_xor | payload | data_xor.
    """
    frames: list[dict] = []
    while True:
        if not buffer:
            return frames
        if buffer[0] != 0x01:
            del buffer[0]
            continue
        if len(buffer) < 8:
            return frames
        length = (buffer[3] << 8) | buffer[4]
        total = 9 + length
        if length > 64 or total > 80:
            del buffer[0]
            continue
        if len(buffer) < total:
            return frames
        frame = bytes(buffer[:total])
        del buffer[:total]
        if _checksum(frame[:7]) != frame[7] or _checksum(frame[8 : 8 + length]) != frame[8 + length]:
            continue
        parsed = _binary_payload((frame[5] << 8) | frame[6], frame[8 : 8 + length])
        if parsed:
            frames.append(parsed)


def _checksum(data: bytes) -> int:
    value = 0
    for byte in data:
        value ^= byte
    return (~value) & 0xFF


def _binary_payload(frame_type: int, data: bytes) -> dict | None:
    import struct

    if frame_type == 0x0A14 and len(data) >= 4 and data[:4] != b"\x00\x00\x00\x00":
        return {"breath_rate_bpm": struct.unpack("<f", data[:4])[0]}
    if frame_type == 0x0A15 and len(data) >= 4 and data[:4] != b"\x00\x00\x00\x00":
        return {"heart_rate_bpm": struct.unpack("<f", data[:4])[0]}
    if frame_type == 0x0F09 and len(data) >= 2:
        return {"human_presence": int.from_bytes(data[:2], "little") != 0}
    if frame_type == 0x0A04 and len(data) >= 4:
        return {"num_targets": int.from_bytes(data[:4], "little")}
    if frame_type == 0x0A16 and len(data) >= 8 and data[0] != 0:
        raw = struct.unpack("<f", data[4:8])[0]
        meters, reported, unit = interpret_distance(raw, None)
        return {"distance_m": meters, "distance_reported": reported, "distance_unit": unit}
    return None


def dummy_sample(seconds: float) -> dict:
    """Labeled stand-in that uses only fields the MR60BHA2 kit can report."""
    import math

    breath = round(15.0 + 1.5 * math.sin(seconds / 3.0), 1)
    heart = round(72.0 + 3.0 * math.sin(seconds / 2.2), 1)
    distance_m = round(0.85 + 0.05 * math.sin(seconds / 5.0), 2)
    return {
        "human_presence": True,
        "breath_rate_bpm": breath,
        "heart_rate_bpm": heart,
        "distance_m": distance_m,
        "num_targets": 1,
        "illuminance_lx": round(160.0 + 25.0 * math.sin(seconds / 4.0), 1),
        "total_phase": None,
        "breath_phase": None,
        "heart_phase": None,
        "stability": "stationary",
        "stale": False,
        "valid": True,
        "firmware": "dummy_mr60bha2",
        "spatial_coordinates_supported": False,
    }
