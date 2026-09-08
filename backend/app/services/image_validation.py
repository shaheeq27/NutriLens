"""Image validation service — checks format, size, and basic integrity."""

from fastapi import UploadFile
from PIL import Image
import io

from app.core.config import settings
from app.utils.errors import ValidationError

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


async def validate_image(file: UploadFile) -> bytes:
    """
    Validate an uploaded image file.

    Returns the raw image bytes if valid.
    Raises ValidationError otherwise.
    """
    # Check content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            f"Unsupported image type: {file.content_type}. "
            f"Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )

    # Read and check size
    image_bytes = await file.read()
    max_bytes = settings.max_image_size_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise ValidationError(
            f"Image exceeds maximum size of {settings.max_image_size_mb}MB"
        )

    # Verify the file is a valid image
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
    except Exception:
        raise ValidationError("File is not a valid image")

    return image_bytes
