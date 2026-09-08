"""
NutriLens backend — photo privacy.

Implements the privacy rules that apply to every uploaded photo regardless
of which scan outcome it leads to: EXIF metadata is stripped before any
other processing, images are never persisted beyond the request, and raw
image bytes / raw OCR text never reach a logger.

Deliberately self-contained, for the same reasons as image_validation.py:
no import from app.contracts.scan_contract (its shape is still
unresolved) and no environment-variable reads (these are fixed privacy
policy, not per-environment secrets).
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator, TypeVar

from PIL import Image, ImageOps

logger = logging.getLogger("nutrilens.photo_privacy")

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Policy constants
# ---------------------------------------------------------------------------

PERSIST_IMAGE_BY_DEFAULT: bool = False        # transient processing only, no permanent storage
MAX_TRANSIENT_RETENTION_SECONDS: int = 300    # upper bound for any temp storage mid-request


# ---------------------------------------------------------------------------
# EXIF stripping
# ---------------------------------------------------------------------------

def strip_exif(data: bytes, decode_fn: Callable[[bytes], Image.Image] | None = None) -> bytes:
    """Removes all EXIF metadata (GPS location, device make/model,
    timestamps, etc). Orientation is baked into the pixel data via
    ImageOps.exif_transpose BEFORE the EXIF block is dropped, so a photo
    taken sideways doesn't silently end up rotated wrong for the user or
    for OCR — stripping metadata must not change what the image looks
    like.

    `decode_fn` lets a caller inject a guarded/timeout-wrapped decoder
    (e.g. image_validation's decode path); by default this uses a plain
    Image.open, since image_validation.validate_image_upload should
    already have been run on `data` before it reaches here."""
    if decode_fn is not None:
        img = decode_fn(data)
    else:
        img = Image.open(io.BytesIO(data))
        img.load()

    transposed = ImageOps.exif_transpose(img)

    out = io.BytesIO()
    transposed.save(out, format=img.format or "JPEG")  # no exif= passed -> none written
    return out.getvalue()


# ---------------------------------------------------------------------------
# Transient storage — guaranteed cleanup
# ---------------------------------------------------------------------------

@contextmanager
def transient_image_store(data: bytes, suffix: str = ".bin") -> Iterator[str]:
    """Writes `data` to a temp file for the duration of the `with` block
    and guarantees deletion afterward — on success or on exception —
    enforcing PERSIST_IMAGE_BY_DEFAULT = False. Logs a warning (does not
    raise, so it never masks a real error from inside the block) if the
    block runs past MAX_TRANSIENT_RETENTION_SECONDS."""
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="nutrilens-")
    start = time.monotonic()
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        yield path
    finally:
        elapsed = time.monotonic() - start
        if os.path.exists(path):
            os.remove(path)
        if elapsed > MAX_TRANSIENT_RETENTION_SECONDS:
            logger.warning(
                "transient image store held for %.1fs, exceeding the %.0fs policy limit",
                elapsed, MAX_TRANSIENT_RETENTION_SECONDS,
            )


# ---------------------------------------------------------------------------
# Log redaction
# ---------------------------------------------------------------------------

# Field names that must never reach a logger, because they may carry raw
# image bytes or raw OCR text (which can include incidental personal data
# captured on a label or in the background of a photo).
_SENSITIVE_LOG_FIELDS = frozenset(
    {"image_bytes", "raw_image", "image_data", "file_bytes", "raw_ocr_text", "ocr_text", "ocr_raw_output"}
)


def redact_for_log(payload: dict[str, Any]) -> dict[str, Any]:
    """Returns a copy of `payload` safe to pass to a logger: known
    sensitive keys AND any raw bytes/bytearray value (regardless of key
    name, as defense in depth) are replaced with a placeholder. Call this
    on anything before it reaches a logger — never log a raw payload
    directly."""
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        is_sensitive_key = key.lower() in _SENSITIVE_LOG_FIELDS
        is_raw_binary = isinstance(value, (bytes, bytearray))
        if is_sensitive_key or is_raw_binary:
            size = len(value) if hasattr(value, "__len__") else "?"
            unit = "chars" if isinstance(value, str) else "bytes"
            redacted[key] = f"<redacted {type(value).__name__}, {size} {unit}>"
        else:
            redacted[key] = value
    return redacted