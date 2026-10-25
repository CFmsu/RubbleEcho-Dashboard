"""Labeled simulation picture and clip. These are not sensor captures."""

import math
import struct
import wave
import zlib
from io import BytesIO

_GLYPHS = {
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10001", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "_": ["00000", "00000", "00000", "00000", "00000", "00000", "11111"],
}


def sample_png(title: str, accent: tuple[int, int, int]) -> bytes:
    width, height = 320, 180
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            if y > 120:
                row.extend((196, 168, 118))
            else:
                shade = 28 + (x + y) % 12
                row.extend((shade, shade + 8, shade + 18))
        rows.append(row)
    _text(rows, 16, 28, "SIMULATION", (232, 238, 246))
    _text(rows, 16, 64, title, accent)
    _text(rows, 16, 148, "SAMPLE FRAME", (232, 238, 246))
    return _png(width, height, rows)


def sample_wav(kind: str) -> tuple[bytes, list[float]]:
    rate = 16000
    count = rate // 2
    samples: list[float] = []
    for index in range(count):
        if kind == "knock":
            value = 0.9 if 80 <= index <= 86 else 0.0
        elif kind == "scratch":
            value = 0.22 if 200 < index < 5000 else 0.0
        else:
            value = 0.01 * math.sin(index / 40.0)
        samples.append(value)
    buffer = BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        frames = b"".join(struct.pack("<h", max(-32767, min(32767, int(sample * 32767)))) for sample in samples)
        handle.writeframes(frames)
    return buffer.getvalue(), samples


def _text(rows: list[bytearray], left: int, top: int, text: str, color: tuple[int, int, int]) -> None:
    cursor = left
    for char in text:
        glyph = _GLYPHS.get(char, _GLYPHS[" "])
        for row_index, bits in enumerate(glyph):
            y = top + row_index * 3
            for bit_index, bit in enumerate(bits):
                if bit != "1":
                    continue
                x0 = cursor + bit_index * 3
                for y_offset in range(3):
                    for x_offset in range(3):
                        _pixel(rows, x0 + x_offset, y + y_offset, color)
        cursor += 18


def _pixel(rows: list[bytearray], x: int, y: int, color: tuple[int, int, int]) -> None:
    if y < 0 or y >= len(rows) or x < 0 or x >= len(rows[0]) // 3:
        return
    offset = x * 3
    rows[y][offset : offset + 3] = bytes(color)


def _png(width: int, height: int, rows: list[bytearray]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
