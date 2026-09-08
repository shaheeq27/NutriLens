"""
Tests for backend/app/services/image_validation.py.
Run with: pytest test_image_validation.py -v
"""

import io
import os
import time

import pytest
from PIL import Image

from image_validation import (
    DecodeError,
    ImageRejectionReason,
    ImageValidationError,
    MAX_FILE_SIZE_BYTES,
    ValidatedImage,
    _check_dimensions,
    _run_with_timeout,
    _sniff_format,
    validate_image_upload,
)


def _jpeg(width: int, height: int, color=(10, 20, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=color).save(buf, format="JPEG")
    return buf.getvalue()


def _png(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (width, height), color=(0, 0, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def _webp(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height)).save(buf, format="WEBP")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Valid images, every allowed format
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("make_image", [_jpeg, _png, _webp])
def test_valid_image_accepted_for_every_allowed_format(make_image):
    data = make_image(300, 300)
    result = validate_image_upload(data)
    assert isinstance(result, ValidatedImage)
    assert result.width == 300 and result.height == 300


# ---------------------------------------------------------------------------
# Every rejection reason, exercised for real
# ---------------------------------------------------------------------------

def test_empty_bytes_rejected():
    result = validate_image_upload(b"")
    assert isinstance(result, ImageValidationError)
    assert result.reason == ImageRejectionReason.EMPTY_OR_CORRUPTED


def test_unsupported_format_rejected():
    result = validate_image_upload(b"GIF89a" + b"\x00" * 50)
    assert isinstance(result, ImageValidationError)
    assert result.reason == ImageRejectionReason.UNSUPPORTED_FORMAT


def test_truncated_image_rejected_as_decode_failed():
    """Right magic bytes, garbage after — must fail at decode, not
    silently succeed with corrupted pixel data."""
    garbage = b"\xff\xd8\xff\xe0" + b"\x00" * 40
    result = validate_image_upload(garbage)
    assert isinstance(result, ImageValidationError)
    assert result.reason == ImageRejectionReason.DECODE_FAILED


def test_below_minimum_dimension_rejected():
    result = validate_image_upload(_jpeg(50, 50))
    assert isinstance(result, ImageValidationError)
    assert result.reason == ImageRejectionReason.DIMENSIONS_OUT_OF_RANGE


def test_above_maximum_dimension_rejected():
    """Deliberately thin (8500 x 50) so the fixture itself stays cheap to
    allocate while still tripping the per-side maximum."""
    result = validate_image_upload(_jpeg(8500, 50))
    assert isinstance(result, ImageValidationError)
    assert result.reason == ImageRejectionReason.DIMENSIONS_OUT_OF_RANGE


def test_file_too_large_rejected():
    oversized = b"\xff\xd8\xff" + b"0" * (MAX_FILE_SIZE_BYTES + 1)
    result = validate_image_upload(oversized)
    assert isinstance(result, ImageValidationError)
    assert result.reason == ImageRejectionReason.FILE_TOO_LARGE


def test_file_too_large_is_checked_before_decode_is_attempted():
    """Size must be checked BEFORE any decode attempt — an oversized file
    that isn't even valid past the magic bytes must still be caught by
    the size check, not attempt-and-fail at decode."""
    oversized_garbage = b"\xff\xd8\xff" + os.urandom(MAX_FILE_SIZE_BYTES + 1)
    result = validate_image_upload(oversized_garbage)
    assert isinstance(result, ImageValidationError)
    assert result.reason == ImageRejectionReason.FILE_TOO_LARGE


# ---------------------------------------------------------------------------
# Dimension/megapixel check as a pure function — the decompression-bomb
# boundary, tested with synthetic integers so we never allocate a real
# huge image just to prove the limit is enforced.
# ---------------------------------------------------------------------------

def test_megapixel_bomb_boundary_pure_function():
    assert _check_dimensions(5000, 5000) is None  # 25 MP, within every bound
    assert _check_dimensions(7000, 7000) == ImageRejectionReason.DIMENSIONS_OUT_OF_RANGE  # 49 MP > 40 MP cap
    assert _check_dimensions(50_000, 50_000) == ImageRejectionReason.DIMENSIONS_OUT_OF_RANGE


def test_magic_byte_sniffing_ignores_declared_mime_type():
    assert _sniff_format(_jpeg(210, 210)) == "image/jpeg"
    assert _sniff_format(_png(210, 210)) == "image/png"
    assert _sniff_format(_webp(210, 210)) == "image/webp"
    assert _sniff_format(b"not an image at all") is None


# ---------------------------------------------------------------------------
# Timeout wrapper — tested directly with a dummy function
# ---------------------------------------------------------------------------

def test_timeout_wrapper_raises_on_slow_function():
    with pytest.raises(DecodeError):
        _run_with_timeout(lambda: time.sleep(2), timeout_seconds=0.2)


def test_timeout_wrapper_passes_through_fast_function():
    assert _run_with_timeout(lambda: "ok", timeout_seconds=1) == "ok"