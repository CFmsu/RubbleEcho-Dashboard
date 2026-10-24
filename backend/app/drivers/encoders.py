import json
import zlib

ALLOWED_COMMANDS = {
    "stop",
    "move_cm",
    "turn_deg",
    "rescan",
    "capture",
    "knock_test_request",
}


def frame_command(payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    crc = zlib.crc32(body.encode("utf-8")) & 0xFFFFFFFF
    return f"{body}|{crc:08x}\n"


def parse_frame(frame: str) -> dict | None:
    text = frame.strip()
    if "|" not in text:
        return None
    body, crc_text = text.rsplit("|", 1)
    expected = f"{zlib.crc32(body.encode('utf-8')) & 0xFFFFFFFF:08x}"
    if crc_text.lower() != expected:
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("type") not in ALLOWED_COMMANDS:
        return None
    return payload
