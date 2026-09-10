"""
Tests for backend/app/services/photo_privacy.py.
Run with: pytest test_photo_privacy.py -v
"""

import io
import logging
import os
import time

import pytest
from PIL import Image

from app.services.photo_privacy import (
    MAX_TRANSIENT_RETENTION_SECONDS,
    redact_for_log,
    strip_exif,
    transient_image_store,
)


def _jpeg(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(1, 2, 3)).save(buf, format="JPEG")
    return buf.getvalue()


def _jpeg_with_exif(width, height, orientation=None, make="TestMake"):
    im = Image.new("RGB", (width, height), color=(1, 2, 3))
    exif = im.getexif()
    exif[271] = make  # Make tag
    if orientation is not None:
        exif[274] = orientation  # Orientation tag
    buf = io.BytesIO()
    im.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# strip_exif — must remove metadata AND preserve visual appearance
# ---------------------------------------------------------------------------

def test_strip_exif_removes_metadata():
    original = _jpeg_with_exif(40, 20, orientation=1)
    before = Image.open(io.BytesIO(original))
    assert dict(before.getexif()) != {}

    cleaned = strip_exif(original)
    after = Image.open(io.BytesIO(cleaned))
    assert dict(after.getexif()) == {}


def test_strip_exif_bakes_in_orientation_instead_of_dropping_it():
    """Orientation 6 requires a 90-degree correction — if strip_exif just
    deleted the tag without applying it, the image would silently end up
    displayed sideways. Dimensions swapping (40x20 -> 20x40) proves the
    rotation was actually baked into the pixel data, not merely
    discarded."""
    original = _jpeg_with_exif(40, 20, orientation=6)
    cleaned = strip_exif(original)
    result = Image.open(io.BytesIO(cleaned))
    assert result.size == (20, 40)
    assert dict(result.getexif()) == {}


def test_strip_exif_is_idempotent_on_already_clean_image():
    clean = _jpeg(40, 20)
    twice = strip_exif(strip_exif(clean))
    assert Image.open(io.BytesIO(twice)).size == (40, 20)


def test_strip_exif_accepts_an_injected_decode_function():
    """image_validation's guarded/timeout-wrapped decoder can be passed
    in instead of the plain default — confirms the composition point
    scan_orchestrator.py will actually use works."""
    calls = []

    def fake_decode(data: bytes) -> Image.Image:
        calls.append(True)
        img = Image.open(io.BytesIO(data))
        img.load()
        return img

    original = _jpeg_with_exif(40, 20, orientation=1)
    cleaned = strip_exif(original, decode_fn=fake_decode)
    assert calls == [True]
    assert dict(Image.open(io.BytesIO(cleaned)).getexif()) == {}


# ---------------------------------------------------------------------------
# transient_image_store — guaranteed cleanup
# ---------------------------------------------------------------------------

def test_transient_store_deletes_file_after_normal_exit():
    with transient_image_store(b"hello", suffix=".bin") as path:
        assert os.path.exists(path)
        saved_path = path
    assert not os.path.exists(saved_path)


def test_transient_store_deletes_file_even_on_exception():
    saved_path = None
    with pytest.raises(RuntimeError):
        with transient_image_store(b"hello", suffix=".bin") as path:
            saved_path = path
            raise RuntimeError("boom")
    assert saved_path is not None
    assert not os.path.exists(saved_path)


def test_transient_store_contents_are_correct_during_the_block():
    with transient_image_store(b"exact bytes", suffix=".bin") as path:
        with open(path, "rb") as f:
            assert f.read() == b"exact bytes"


def test_transient_store_warns_past_retention_limit(monkeypatch, caplog):
    import app.services.photo_privacy as pp

    monkeypatch.setattr(pp, "MAX_TRANSIENT_RETENTION_SECONDS", 0.05)
    with caplog.at_level(logging.WARNING, logger="nutrilens.photo_privacy"):
        with transient_image_store(b"x", suffix=".bin"):
            time.sleep(0.15)
    assert any("exceeding" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# redact_for_log
# ---------------------------------------------------------------------------

def test_redact_known_sensitive_keys():
    out = redact_for_log({"raw_ocr_text": "some label text", "image_bytes": b"\x00" * 10})
    assert "some label text" not in str(out)
    assert out["raw_ocr_text"].startswith("<redacted")
    assert out["image_bytes"].startswith("<redacted")


def test_redact_leaves_safe_fields_untouched():
    out = redact_for_log({"food_name": "banana", "confidence": "high"})
    assert out == {"food_name": "banana", "confidence": "high"}


def test_redact_catches_raw_bytes_under_any_key_name():
    """Defense in depth: even an unexpectedly-named field is redacted if
    its value is raw bytes."""
    out = redact_for_log({"totally_unnamed_field": b"\x01\x02\x03"})
    assert out["totally_unnamed_field"].startswith("<redacted")