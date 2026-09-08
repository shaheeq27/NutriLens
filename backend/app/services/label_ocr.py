"""Label OCR service — extracts text from packaged food nutrition labels."""


async def extract_label_text(image_bytes: bytes) -> dict:
    """
    Perform OCR on a food label image to extract nutritional text.

    Returns a dict with:
      - raw_text: str
      - ingredients: list[str]
      - serving_size: str | None
    """
    # TODO: Integrate with Gemini Vision API for OCR
    return {
        "raw_text": "",
        "ingredients": [],
        "serving_size": None,
    }
