from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np
from PIL import Image

class OcrProviderError(Exception):
    pass

@dataclass(frozen=True)
class OcrExtractionResult:
    raw_text_blocks: tuple[str, ...]
    provider_confidence: float

@runtime_checkable
class OcrProvider(Protocol):
    def extract_text(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> OcrExtractionResult: ...

class MockOcrProvider:
    def __init__(self, canned_result: OcrExtractionResult):
        self._canned_result = canned_result

    def extract_text(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> OcrExtractionResult:
        return self._canned_result

class EasyOcrProvider:
    """Real implementation using EasyOCR for local/free text extraction."""

    def __init__(self, languages: list[str] = None):
        if languages is None:
            languages = ["en"]
        import easyocr
        # Disable GPU for wide compatibility, though it will be slower
        self._reader = easyocr.Reader(languages, gpu=False)

    def extract_text(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> OcrExtractionResult:
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            # EasyOCR expects a numpy array
            image_np = np.array(image)

            # detail=1 returns bounding box, text, and confidence
            # format: [[bbox, text, conf], ...]
            results = self._reader.readtext(image_np, detail=1)

            if not results:
                return OcrExtractionResult(
                    raw_text_blocks=(),
                    provider_confidence=0.0
                )

            blocks = []
            total_conf = 0.0

            for _, text, conf in results:
                blocks.append(text)
                total_conf += float(conf)

            avg_conf = total_conf / len(results) if results else 0.0

            return OcrExtractionResult(
                raw_text_blocks=tuple(blocks),
                provider_confidence=avg_conf
            )
        except Exception as exc:
            raise OcrProviderError(f"EasyOCR extraction failed: {exc}") from exc
