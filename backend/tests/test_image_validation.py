"""Tests for the image validation service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from io import BytesIO
from PIL import Image

from app.services.image_validation import validate_image
from app.utils.errors import ValidationError


def _make_test_image(fmt: str = "PNG", size: tuple = (100, 100)) -> bytes:
    """Create a minimal valid image in memory."""
    img = Image.new("RGB", size, color="red")
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _make_upload_file(content: bytes, content_type: str = "image/png") -> MagicMock:
    """Create a mock UploadFile."""
    mock = MagicMock()
    mock.content_type = content_type
    mock.read = AsyncMock(return_value=content)
    return mock


@pytest.mark.asyncio
async def test_valid_image_passes():
    """A valid PNG image should pass validation."""
    image_bytes = _make_test_image()
    upload = _make_upload_file(image_bytes, "image/png")
    result = await validate_image(upload)
    assert result == image_bytes


@pytest.mark.asyncio
async def test_invalid_content_type_rejected():
    """An unsupported content type should raise ValidationError."""
    upload = _make_upload_file(b"data", "application/pdf")
    with pytest.raises(ValidationError):
        await validate_image(upload)


@pytest.mark.asyncio
async def test_corrupt_image_rejected():
    """A file that isn't a valid image should raise ValidationError."""
    upload = _make_upload_file(b"not an image", "image/png")
    with pytest.raises(ValidationError):
        await validate_image(upload)
