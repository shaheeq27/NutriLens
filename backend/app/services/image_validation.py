"""
NutriLens backend — image upload validation.

Enforces size, format, magic-byte, dimension/megapixel, and decode-timeout
limits on every uploaded image (raw-food photo, package front, or back/side
label) BEFORE any vendor (vision/OCR) API call is made.

Deliberately self-contained:
- Does NOT import from app.contracts.scan_contract. That file's real shape
  is still unresolved (see project brief §6/§9 discussion) — importing
  from it here would either fail outright or silently couple this module
  to an unconfirmed schema. This module defines its own minimal result
  types (ValidatedImage / ImageValidationError) instead. Mapping between
  these and the eventual contract's `image_rejected` / equivalent state is
  scan_orchestrator.py's job, not this file's.
- Takes no credentials and reads no environment variables, so it has zero
  dependency on the .env.example naming conflict either.

Known limitation, stated plainly rather than glossed over: the decode
timeout below runs decoding in a worker thread and gives up *waiting*
after MAX_DECODE_SECONDS, but Python cannot forcibly kill a native
(libjpeg/libpng/libwebp) decode loop running in a thread — a
sufficiently adversarial file can still burn CPU in the background after
we've moved on and returned a rejection to the caller. The header-only
dimension check below (checking declared width/height before the
expensive full pixel decode) catches the common decompression-bomb shape
and is what actually protects this endpoint; the timeout is a second,
imperfect layer on top of it. A hard per-file resource limit (a
subprocess with a memory/CPU ulimit, or an isolated image-processing
service) is the production-grade fix if this ever needs to be airtight.
"""

from __future__ import annotations

import io
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, TypeVar, Union

from PIL import Image, UnidentifiedImageError

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Policy constants — fixed application policy, not per-environment secrets,
# so these live here rather than in core/config.py.
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES: int = 8 * 1024 * 1024  # 8 MB
ALLOWED_MIME_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp"})
MIN_DIMENSION_PX: int = 200
MAX_DIMENSION_PX: int = 8000
MAX_MEGAPIXELS: float = 40.0  # guards decompression bombs even under MAX_DIMENSION_PX
MAX_DECODE_SECONDS: float = 3.0  # abort decode past this; treat as decode_failed


class ImageRejectionReason(str, Enum):
    """Stable string values — safe to serialize directly into whatever the
    real contract's rejection reason field turns out to be."""

    EMPTY_OR_CORRUPTED = "empty_or_corrupted"
    FILE_TOO_LARGE = "file_too_large"
    UNSUPPORTED_FORMAT = "unsupported_format"
    DIMENSIONS_OUT_OF_RANGE = "dimensions_out_of_range"
    DECODE_FAILED = "decode_failed"


@dataclass(frozen=True)
class ValidatedImage:
    data: bytes
    format: str  # "image/jpeg" | "image/png" | "image/webp"
    width: int
    height: int
    size_bytes: int


@dataclass(frozen=True)
class ImageValidationError:
    reason: ImageRejectionReason
    message: str


ImageValidationResult = Union[ValidatedImage, ImageValidationError]


class DecodeError(Exception):
    """Raised internally when decoding fails or times out."""


class _DimensionsOutOfRange(Exception):
    """Internal control-flow signal only — never escapes this module."""


# Module-level pool: fine for this service's scope. If NutriLens ever runs
# with multiple worker processes behind Cloud Run, each process gets its
# own pool, which is the desired behavior — no shared state needed.
_decode_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="img-decode")


def _run_with_timeout(fn: Callable[[], T], timeout_seconds: float) -> T:
    """Run fn() in a worker thread and enforce a wall-clock timeout. Kept
    separate from image-specific logic so the timeout mechanism itself can
    be unit-tested with a plain dummy function."""
    future = _decode_executor.submit(fn)
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeoutError as exc:
        raise DecodeError(f"operation exceeded {timeout_seconds}s timeout") from exc


def _sniff_format(data: bytes) -> Optional[str]:
    """Identify format from actual file bytes. Never trust a
    client-supplied MIME type or file extension alone."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _check_dimensions(width: int, height: int) -> Optional[ImageRejectionReason]:
    """Pure function, no decoding involved: returns a rejection reason if
    the given dimensions violate policy, else None. Kept separate from
    decode logic so the megapixel-bomb boundary can be unit-tested with
    synthetic large integers, without allocating a real huge image."""
    if width < MIN_DIMENSION_PX or height < MIN_DIMENSION_PX:
        return ImageRejectionReason.DIMENSIONS_OUT_OF_RANGE
    if width > MAX_DIMENSION_PX or height > MAX_DIMENSION_PX:
        return ImageRejectionReason.DIMENSIONS_OUT_OF_RANGE
    if (width * height) / 1_000_000 > MAX_MEGAPIXELS:
        return ImageRejectionReason.DIMENSIONS_OUT_OF_RANGE
    return None


def validate_image_upload(data: bytes) -> ImageValidationResult:
    """Enforces the module's policy end to end: size, magic bytes,
    dimensions/megapixels (checked from the header before any full pixel
    decode), and a decode timeout. Returns ValidatedImage on success or an
    ImageValidationError describing why the upload was rejected."""
    if not data:
        return ImageValidationError(
            reason=ImageRejectionReason.EMPTY_OR_CORRUPTED,
            message="No image data received.",
        )

    if len(data) > MAX_FILE_SIZE_BYTES:
        limit_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        return ImageValidationError(
            reason=ImageRejectionReason.FILE_TOO_LARGE,
            message=f"Image exceeds the {limit_mb} MB limit.",
        )

    fmt = _sniff_format(data)
    if fmt is None or fmt not in ALLOWED_MIME_TYPES:
        return ImageValidationError(
            reason=ImageRejectionReason.UNSUPPORTED_FORMAT,
            message="Only JPEG, PNG, and WebP images are supported.",
        )

    def _decode() -> Image.Image:
        # Image.open() parses the header without decoding pixel data —
        # this is the cheap step. Dimensions are checked here, BEFORE
        # .load() below performs the expensive full decode: a file with
        # huge declared dimensions is rejected before we ever try to
        # materialize its pixel buffer.
        img = Image.open(io.BytesIO(data))
        reason = _check_dimensions(*img.size)
        if reason:
            raise _DimensionsOutOfRange(reason)
        img.load()
        return img

    try:
        img = _run_with_timeout(_decode, MAX_DECODE_SECONDS)
    except _DimensionsOutOfRange:
        return ImageValidationError(
            reason=ImageRejectionReason.DIMENSIONS_OUT_OF_RANGE,
            message=(
                f"Image dimensions must be between {MIN_DIMENSION_PX} and "
                f"{MAX_DIMENSION_PX} px per side."
            ),
        )
    except (DecodeError, UnidentifiedImageError, OSError):
        return ImageValidationError(
            reason=ImageRejectionReason.DECODE_FAILED,
            message="This image could not be decoded. Please try a different photo.",
        )

    width, height = img.size
    return ValidatedImage(data=data, format=fmt, width=width, height=height, size_bytes=len(data))