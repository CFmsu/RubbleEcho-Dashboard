"""A spoken briefing and a one-page PDF a person can hand to someone at the table."""

from __future__ import annotations

import struct
import zlib
from typing import Any

_SOUND = {
    "knock": "a sharp knock",
    "scratch": "a scraping sound",
    "scratch/scrape": "a scraping sound",
    "ambient": "only the room",
    "silence": "nothing",
    "unknown": "no clear sound",
}


def narrate(heatmap: list[dict], point_id: str | None) -> str:
    cells = [point for point in heatmap or [] if isinstance(point, dict) and point.get("point_id")]
    cells.sort(key=lambda point: -(float(point.get("score") or 0)))
    lead = point_id or (str(cells[0]["point_id"]) if cells else None)
    if not lead:
        return (
            "The rover has not finished a stop yet. "
            "When it does, this briefing will say what was heard, whether a pulse showed up, "
            "and which square to walk to first. The picture will be the frame from that stop."
        )
    chosen = next((point for point in cells if str(point.get("point_id")) == lead), None)
    readings = (chosen or {}).get("readings") if isinstance((chosen or {}).get("readings"), dict) else {}
    sound = _SOUND.get(str(readings.get("sound") or "unknown"), "no clear sound")
    presence = readings.get("radar_presence")
    if presence is True or presence == "present":
        pulse = "the radar also thought something was moving there"
    elif presence is False or presence == "absent":
        pulse = "the radar stayed quiet there"
    else:
        pulse = "the radar did not give a clear answer there"
    distance = readings.get("distance_m")
    range_line = ""
    if isinstance(distance, (int, float)) and not isinstance(distance, bool):
        range_line = f" It put that movement about {distance:.1f} meters out."
    others = [str(point["point_id"]) for point in cells if str(point["point_id"]) != lead][:2]
    next_line = (
        f" After that, look at {others[0]}" + (f" and then {others[1]}" if len(others) > 1 else "") + "."
        if others
        else ""
    )
    return (
        f"Walk to {lead} first. That is the square that stood out. "
        f"At that stop we heard {sound}, and {pulse}.{range_line} "
        f"The picture on this page is the camera frame from that stop."
        f"{next_line} "
        "This is a place to check. It is not a claim that someone is under the sand, "
        "and it does not tell the rover to move."
    )


def _ranked(heatmap: list[dict] | None) -> list[str]:
    cells = [point for point in heatmap or [] if isinstance(point, dict) and point.get("point_id")]
    cells.sort(key=lambda point: -(float(point.get("score") or 0)))
    return [str(point["point_id"]) for point in cells]


def _lead_id(heatmap: list[dict] | None) -> str | None:
    ranked = _ranked(heatmap)
    return ranked[0] if ranked else None


def align_narrative(written: str | None, heatmap: list[dict] | None, point_id: str | None) -> str:
    """Keep the model's sentences, and name the next square the readings actually rank second."""
    ranked = _ranked(heatmap)
    lead = str(point_id) if point_id else (ranked[0] if ranked else None)
    local = narrate(list(heatmap or []), lead)
    if not isinstance(written, str) or len(written.strip()) < 40 or not lead or lead not in written:
        return local
    text = written.strip()
    if len(ranked) < 2 or ranked[1] in text:
        return text
    second = ranked[1]
    kept = []
    for sentence in text.replace("!", ".").split("."):
        sentence = sentence.strip()
        if not sentence:
            continue
        if any(cell != lead and cell in sentence for cell in ranked):
            continue
        kept.append(sentence)
    if not kept:
        return local
    return f"{'. '.join(kept)}. After that, look at {second}."


def briefing_pdf(state: Any) -> bytes:
    reasoning = state.reasoning if isinstance(state.reasoning, dict) else {}
    written = reasoning.get("narrative")
    point = None
    recommendation = reasoning.get("recommendation")
    if isinstance(recommendation, dict):
        point = recommendation.get("point_id")
    lead = str(point) if point else _lead_id(state.heatmap)
    written = align_narrative(written if isinstance(written, str) else None, list(state.heatmap or []), lead)
    image = _photo(state, lead)
    title = "RubbleEcho briefing"
    note = "Read this aloud at the table. The picture is the stored frame from the stop named above."
    return _pdf(title, written.strip(), note, image)


def _photo(state: Any, point_id: str | None) -> tuple[int, int, bytes] | None:
    from app.services import sim_run

    path = sim_run.media_file("camera", point_id)
    raw = path.read_bytes() if path is not None and path.is_file() else None
    if raw is None and isinstance(state.media_camera, (bytes, bytearray)) and state.media_camera[:8] == b"\x89PNG\r\n\x1a\n":
        raw = bytes(state.media_camera)
    if not raw:
        return None
    return _png_rgb(raw)


def _png_rgb(data: bytes) -> tuple[int, int, bytes] | None:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos = 8
    width = height = color = 0
    chunks = []
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        kind = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR" and len(chunk) >= 13:
            width, height, depth, color = struct.unpack(">IIBB", chunk[:10])
            if depth != 8 or color not in {2, 6} or chunk[10] != 0:
                return None
        elif kind == b"IDAT":
            chunks.append(chunk)
        elif kind == b"IEND":
            break
    if not width or not chunks:
        return None
    channels = 3 if color == 2 else 4
    try:
        inflated = zlib.decompress(b"".join(chunks))
    except zlib.error:
        return None
    stride = width * channels
    rows = []
    cursor = 0
    previous = bytearray(stride)
    for _ in range(height):
        if cursor >= len(inflated):
            return None
        filter_type = inflated[cursor]
        cursor += 1
        row = bytearray(inflated[cursor : cursor + stride])
        cursor += stride
        if len(row) != stride:
            return None
        _unfilter(filter_type, row, previous, channels)
        previous = row
        if channels == 4:
            row = bytearray(row[index] for index in range(len(row)) if index % 4 != 3)
        rows.append(bytes(row))
    return width, height, b"".join(rows)


def _unfilter(kind: int, row: bytearray, previous: bytearray, channels: int) -> None:
    for index, value in enumerate(row):
        left = row[index - channels] if index >= channels else 0
        up = previous[index]
        if kind == 1:
            row[index] = (value + left) & 255
        elif kind == 2:
            row[index] = (value + up) & 255
        elif kind == 3:
            row[index] = (value + ((left + up) // 2)) & 255
        elif kind == 4:
            upper_left = previous[index - channels] if index >= channels else 0
            row[index] = (value + _paeth(left, up, upper_left)) & 255


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    choices = ((abs(estimate - left), left), (abs(estimate - up), up), (abs(estimate - upper_left), upper_left))
    return min(choices)[1]


def _pdf(title: str, body: str, note: str, image: tuple[int, int, bytes] | None) -> bytes:
    lines = _wrap(body, 88)
    commands = ["BT", "/F1 20 Tf", "54 740 Td", f"({_escape(title)}) Tj", "/F1 12 Tf"]
    y = 704
    for line in lines:
        commands.append(f"1 0 0 1 54 {y} Tm ({_escape(line)}) Tj")
        y -= 16
    y -= 8
    commands.append(f"1 0 0 1 54 {y} Tm ({_escape(note)}) Tj")
    commands.append("ET")
    image_object = None
    if image is not None:
        width, height, rgb = image
        draw_w = 460
        draw_h = max(80, int(draw_w * height / max(width, 1)))
        if draw_h > 280:
            draw_h = 280
            draw_w = max(120, int(draw_h * width / max(height, 1)))
        commands.append(f"q {draw_w} 0 0 {draw_h} 54 {max(48, y - draw_h - 18)} cm /Im0 Do Q")
        image_object = (width, height, zlib.compress(rgb))
    content = "\n".join(commands).encode("latin-1", errors="replace")
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>")
    resources = b"/Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >>"
    if image_object is not None:
        resources += b" /XObject << /Im0 6 0 R >>"
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << "
        + resources
        + b" >> /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
    if image_object is not None:
        width, height, compressed = image_object
        header = (
            f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
            f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length {len(compressed)} >>\nstream\n"
        ).encode()
        objects.append(header + compressed + b"\nendstream")
    return _assemble(objects)


def _wrap(text: str, width: int) -> list[str]:
    lines = []
    for paragraph in text.splitlines() or [text]:
        words = paragraph.split()
        current = ""
        for word in words:
            trial = word if not current else f"{current} {word}"
            if len(trial) > width:
                if current:
                    lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
        lines.append("")
    return lines[:28]


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _assemble(objects: list[bytes]) -> bytes:
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return bytes(output)
