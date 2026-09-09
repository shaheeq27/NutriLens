"""
NutriLens backend — Google Cloud Vision OCR provider.

Extracts raw text from a nutrition-label photo using
`document_text_detection` — purpose-built for dense printed text, per the
project's tech stack notes. This module's job stops at raw text
extraction; turning that text into structured nutrient values (and
judging whether it's blurry/partial/wrong layout) is services/label_ocr.py's
job, not this one. Keeping that boundary means this file has exactly one
failure surface to reason about: did the vendor call succeed and find
text, or not.

Deliberately self-contained, same reasoning as the other Lane B provider
files: no import from app.contracts.scan_contract (still unresolved),
and credentials are constructor parameters, not environment reads — this
has no dependency on the .env.example naming conflict.

Verified against the actual installed SDK (google-cloud-vision==3.15.0,
pinned in requirements.txt): `ImageAnnotatorClient.document_text_detection`,
the `Feature.Type.DOCUMENT_TEXT_DETECTION`-backed convenience method, and
the response shape (`full_text_annotation.text`, `error.message`) were
all checked directly against the installed client, not assumed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Protocol, Union, runtime_checkable


class OcrProviderError(Exception):
    """Raised when the OCR provider fails outright — a network/API error,
    not a 'this label was unreadable' business outcome (that's
    represented by OcrRejection instead, a normal return value)."""


class OcrRejectionReason(str, Enum):
    NO_TEXT_DETECTED = "no_text_detected"
    API_ERROR = "api_error"


@dataclass(frozen=True)
class OcrResult:
    raw_text: str


@dataclass(frozen=True)
class OcrRejection:
    reason: OcrRejectionReason
    message: str


OcrOutcome = Union[OcrResult, OcrRejection]


@runtime_checkable
class OcrProvider(Protocol):
    def extract_text(self, image_bytes: bytes) -> OcrOutcome: ...


class MockOcrProvider:
    """Returns a fixed, caller-supplied outcome regardless of input
    image — per the project's 'mock providers first' rule."""

    def __init__(self, canned_outcome: OcrOutcome):
        self._canned_outcome = canned_outcome

    def extract_text(self, image_bytes: bytes) -> OcrOutcome:
        return self._canned_outcome


class GoogleVisionOcrProvider:
    """Real implementation. `client` can be injected for testing — see
    test_google_vision.py, which never touches the network."""

    def __init__(self, credentials_path: Optional[str] = None, client: Any = None):
        if client is not None:
            self._client = client
        else:
            from google.cloud import vision  # imported lazily, same reasoning as openai_vision.py

            # credentials_path, if given, is passed through explicitly
            # rather than relying on the ambient GOOGLE_APPLICATION_CREDENTIALS
            # environment variable being set correctly by something else —
            # keeps this provider's credential source explicit and testable.
            if credentials_path:
                self._client = vision.ImageAnnotatorClient.from_service_account_file(credentials_path)
            else:
                self._client = vision.ImageAnnotatorClient()

    def extract_text(self, image_bytes: bytes) -> OcrOutcome:
        from google.cloud import vision  # always needed to build the request object

        image = vision.Image(content=image_bytes)
        try:
            response = self._client.document_text_detection(image=image)
        except Exception as exc:
            raise OcrProviderError(f"Google Cloud Vision request failed: {exc}") from exc

        if response.error.message:
            raise OcrProviderError(f"Google Cloud Vision returned an error: {response.error.message}")

        text = response.full_text_annotation.text
        if not text or not text.strip():
            return OcrRejection(
                reason=OcrRejectionReason.NO_TEXT_DETECTED,
                message="No text was found on this label. Please try a clearer photo.",
            )

        return OcrResult(raw_text=text)