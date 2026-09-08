"""Photo privacy service — strips EXIF and sensitive metadata before processing."""

from PIL import Image
import io


def strip_metadata(image_bytes: bytes) -> bytes:
    """
    Remove EXIF and other metadata from an image for privacy.

    Returns clean image bytes with metadata stripped.
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Create a new image without metadata
    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))

    output = io.BytesIO()
    clean.save(output, format=img.format or "PNG")
    return output.getvalue()
