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

_CATEGORY = {
    "knock": "knock",
    "periodic_tapping": "knock",
    "scratch": "scrape",
    "scratch/scrape": "scrape",
    "ambient": "room",
    "listening": "room",
    "silence": "quiet",
}


def sound_category(label: str | None) -> str:
    """The processed microphone label the model is allowed to repeat."""
    if not label:
        return "not_heard"
    return _CATEGORY.get(str(label), "unclassified")


def narrate(heatmap: list[dict], point_id: str | None) -> str:
    cells = [point for point in heatmap or [] if isinstance(point, dict) and point.get("point_id")]
    cells.sort(key=lambda point: -(float(point.get("score") or 0)))
    lead = point_id or (str(cells[0]["point_id"]) if cells else None)
    if not lead:
        return (
            "The rover has not finished a stop yet. "
            "When it does, this briefing will name the microphone and the other stored readings "
            "and which square to check, if those readings distinguish one."
        )
    from app.services.cell_visit import place_name

    chosen = next((point for point in cells if str(point.get("point_id")) == lead), None)
    readings = (chosen or {}).get("readings") if isinstance((chosen or {}).get("readings"), dict) else {}
    sound = _SOUND.get(str(readings.get("sound") or "unknown"), "no clear sound")
    presence = readings.get("radar_presence")
    if presence is True or presence == "present":
        radar_words = "the radar reported a return"
    elif presence is False or presence == "absent":
        radar_words = "the radar reported no return"
    else:
        radar_words = "the radar added no return of its own"
    range_line = ""
    distance = readings.get("distance_m")
    if isinstance(distance, (int, float)) and not isinstance(distance, bool):
        range_line = f" It put that return about {distance:.1f} meters out."
    ultra = readings.get("ultrasonic_cm")
    if isinstance(ultra, (int, float)) and not isinstance(ultra, bool):
        range_line += f" The ultrasonic read {float(ultra):.0f} centimeters ahead."
    others = [place_name(str(point["point_id"])) for point in cells if str(point["point_id"]) != lead][:2]
    if not others:
        next_line = ""
    elif len(others) == 1:
        next_line = f" After that, look at {others[0]}."
    else:
        next_line = f" After that, look at {others[0]} and then {others[1]}."
    spoken = place_name(lead)
    return (
        f"Walk to {spoken} first. That is the square that stood out. "
        f"At that stop we heard {sound}, and {radar_words}.{range_line}"
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


_DRIVE = ("r1c1", "r1c2", "r1c3", "r2c3", "r2c2", "r2c1", "r3c1", "r3c2", "r3c3")


def _session_points(state: Any) -> list[dict]:
    points = list(getattr(state, "heatmap", None) or [])
    if not points:
        points = list(getattr(state, "cell_captures", None) or [])
    clean = [point for point in points if isinstance(point, dict) and point.get("point_id")]
    order = {cell: index for index, cell in enumerate(_DRIVE)}
    return sorted(clean, key=lambda point: (order.get(str(point.get("point_id")), 100), str(point.get("point_id"))))


def _hearing(readings: dict) -> str:
    raw = readings.get("sound") or readings.get("sound_category")
    labels = {
        "knock": "Knock",
        "periodic_tapping": "Knock",
        "scratch": "Scrape",
        "scratch/scrape": "Scrape",
        "scrape": "Scrape",
        "ambient": "Room",
        "room": "Room",
        "listening": "Room",
        "silence": "Quiet",
        "quiet": "Quiet",
    }
    if not isinstance(raw, str) or not raw.strip():
        return "-"
    return labels.get(raw, raw.replace("_", " ").capitalize())


def _reading_table(points: list[dict]) -> list[list[str]]:
    from app.services.cell_visit import place_name

    rows = [["Square", "Microphone", "Ultrasonic", "Radar", "Return"]]
    for point in points:
        readings = point.get("readings") if isinstance(point.get("readings"), dict) else {}
        ultra = readings.get("ultrasonic_cm")
        distance = readings.get("distance_m")
        presence = readings.get("radar_presence")
        if presence is True or presence == "present":
            flag = "Set"
        elif presence is False or presence == "absent":
            flag = "Clear"
        else:
            flag = "-"
        ultra_text = f"{float(ultra):.0f} cm" if isinstance(ultra, (int, float)) and not isinstance(ultra, bool) else "-"
        radar_text = f"{float(distance):.2f} m" if isinstance(distance, (int, float)) and not isinstance(distance, bool) else "-"
        rows.append([place_name(str(point["point_id"])), _hearing(readings), ultra_text, radar_text, flag])
    return rows


def briefing_pdf(state: Any) -> bytes:
    reasoning = state.reasoning if isinstance(state.reasoning, dict) else {}
    written = reasoning.get("narrative")
    points = _session_points(state)
    point = None
    recommendation = reasoning.get("recommendation")
    if isinstance(recommendation, dict):
        point = recommendation.get("point_id")
    lead = str(point) if point else _lead_id(points)
    written = align_narrative(written if isinstance(written, str) else None, points, lead)
    image = _photo(state, lead)
    trial = getattr(state, "trial_id", None)
    subtitle = f"Trial {trial}" if trial else "Session report"
    note = "Read the narration at the table. The table is the stored readings from this session."
    return _pdf(
        "RubbleEcho report",
        written.strip(),
        note,
        image,
        subtitle=subtitle,
        table=_reading_table(points) if points else None,
    )


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


def _pdf(
    title: str,
    body: str,
    note: str,
    image: tuple[int, int, bytes] | None,
    *,
    subtitle: str = "",
    table: list[list[str]] | None = None,
) -> bytes:
    commands = [
        "0.102 0.165 0.322 rg",
        "0 746 612 46 re f",
        "1 1 1 rg",
        "BT",
        "/F2 18 Tf",
        f"1 0 0 1 48 768 Tm ({_escape(title)}) Tj",
        "/F1 10 Tf",
        f"1 0 0 1 48 754 Tm ({_escape(subtitle or 'Session report')}) Tj",
        "ET",
        "0.12 0.16 0.28 rg",
        "BT",
        "/F2 11 Tf",
        "1 0 0 1 48 726 Tm (Narration) Tj",
        "ET",
        "0.16 0.18 0.22 rg",
        "BT",
        "/F1 11 Tf",
    ]
    y = 708
    for line in _wrap(body, 86):
        if y < 360:
            break
        commands.append(f"1 0 0 1 48 {y} Tm ({_escape(line)}) Tj")
        y -= 15
    commands.append("ET")
    y -= 10
    if table:
        y = _table(commands, table, y)
    y -= 8
    commands.extend(
        [
            "0.35 0.38 0.44 rg",
            "BT",
            "/F1 9 Tf",
            f"1 0 0 1 48 {max(36, y)} Tm ({_escape(note)}) Tj",
            "ET",
        ]
    )
    image_object = None
    if image is not None:
        width, height, rgb = image
        room = max(36, y) - 48
        draw_w = 220
        draw_h = max(48, int(draw_w * height / max(width, 1)))
        if draw_h > room and room > 60:
            draw_h = room
            draw_w = max(80, int(draw_h * width / max(height, 1)))
        image_top = max(36, y) - 18
        if draw_h + 36 < image_top:
            commands.append(f"q {draw_w} 0 0 {draw_h} 48 {image_top - draw_h} cm /Im0 Do Q")
        image_object = (width, height, zlib.compress(rgb))
    content = "\n".join(commands).encode("latin-1", errors="replace")
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>")
    resources = (
        b"/Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> "
        b"/F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> >>"
    )
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


def _table(commands: list[str], rows: list[list[str]], y: int) -> int:
    columns = (48, 200, 310, 400, 490)
    height = 16
    commands.extend(
        [
            "0.12 0.16 0.28 rg",
            "BT",
            "/F2 11 Tf",
            f"1 0 0 1 48 {y} Tm (Recorded readings) Tj",
            "ET",
        ]
    )
    y -= 20
    for index, row in enumerate(rows[:13]):
        if y < 56:
            break
        if index == 0:
            commands.append("0.90 0.92 0.95 rg")
        elif index % 2 == 0:
            commands.append("0.96 0.97 0.98 rg")
        else:
            commands.append("1 1 1 rg")
        commands.append(f"48 {y - 4} 516 {height} re f")
        commands.append("0.12 0.16 0.28 rg" if index == 0 else "0.16 0.18 0.22 rg")
        commands.append("BT")
        commands.append("/F2 9 Tf" if index == 0 else "/F1 9 Tf")
        for column, text in zip(columns, row):
            commands.append(f"1 0 0 1 {column} {y} Tm ({_escape(str(text)[:28])}) Tj")
        commands.append("ET")
        y -= height
    return y - 6


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
