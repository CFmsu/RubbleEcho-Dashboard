"""Decode an uploaded iPhone photograph into a browser-displayable JPEG."""

from __future__ import annotations

import io

from PIL import Image, UnidentifiedImageError

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:  # pragma: no cover - exercised only when the extra is missing
    HEIC_SUPPORTED = False


class ImageDecodeError(ValueError):
    pass


def decode_upload(payload: bytes, media_type: str) -> tuple[bytes, int, int]:
    if media_type in {"image/heic", "image/heif"} and not HEIC_SUPPORTED:
        raise ImageDecodeError("HEIC/HEIF support is not installed. Export the photo as JPEG or PNG.")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            rgb = image.convert("RGB")
            width, height = rgb.size
            if width < 2 or height < 2:
                raise ImageDecodeError("image is too small to place a 4×4 grid")
            buffer = io.BytesIO()
            rgb.save(buffer, format="JPEG", quality=90)
    except UnidentifiedImageError as exc:
        raise ImageDecodeError("file is not a readable JPEG, PNG, or HEIC image") from exc
    except OSError as exc:
        raise ImageDecodeError("file could not be decoded") from exc
    return buffer.getvalue(), width, height
