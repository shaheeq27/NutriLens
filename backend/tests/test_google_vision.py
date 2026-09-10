"""
Tests for backend/app/providers/google_vision.py.
Run with: pytest test_google_vision.py -v

No real Google Cloud credentials or network access is used — the client
is always a fake/stub injected via the `client=` constructor parameter.
"""

import pytest
from google.cloud import vision

from google_vision import (
    GoogleVisionOcrProvider,
    MockOcrProvider,
    OcrProviderError,
    OcrRejection,
    OcrRejectionReason,
    OcrResult,
)


# ---------------------------------------------------------------------------
# Fake Google Cloud Vision client
# ---------------------------------------------------------------------------

class _FakeAnnotateResponse:
    def __init__(self, text: str = "", error_message: str = ""):
        self.full_text_annotation = type("FTA", (), {"text": text})()
        self.error = type("Err", (), {"message": error_message})()


class _FakeVisionClient:
    def __init__(self, text: str = "", error_message: str = "", exception=None):
        self._text = text
        self._error_message = error_message
        self._exception = exception
        self.last_image = None

    def document_text_detection(self, image):
        self.last_image = image
        if self._exception is not None:
            raise self._exception
        return _FakeAnnotateResponse(text=self._text, error_message=self._error_message)


# ---------------------------------------------------------------------------
# MockOcrProvider
# ---------------------------------------------------------------------------

def test_mock_provider_returns_canned_outcome_regardless_of_input():
    canned = OcrResult(raw_text="Calories 140")
    provider = MockOcrProvider(canned)
    assert provider.extract_text(b"anything") is canned
    assert provider.extract_text(b"") is canned


# ---------------------------------------------------------------------------
# GoogleVisionOcrProvider — success and rejection paths
# ---------------------------------------------------------------------------

def test_successful_extraction_returns_raw_text():
    client = _FakeVisionClient(text="Nutrition Facts\nCalories 140\nProtein 2g")
    provider = GoogleVisionOcrProvider(client=client)
    result = provider.extract_text(b"fake image bytes")
    assert isinstance(result, OcrResult)
    assert "Calories 140" in result.raw_text


def test_request_uses_a_real_vision_image_object():
    """Confirms the provider builds a genuine vision.Image, not some
    ad-hoc shape — so a fake client in tests sees the same request shape
    production code would send."""
    client = _FakeVisionClient(text="some text")
    provider = GoogleVisionOcrProvider(client=client)
    provider.extract_text(b"\x01\x02\x03")
    assert isinstance(client.last_image, vision.Image)
    assert client.last_image.content == b"\x01\x02\x03"


def test_empty_text_result_is_a_rejection_not_an_error():
    client = _FakeVisionClient(text="")
    provider = GoogleVisionOcrProvider(client=client)
    result = provider.extract_text(b"fake image bytes")
    assert isinstance(result, OcrRejection)
    assert result.reason == OcrRejectionReason.NO_TEXT_DETECTED


def test_whitespace_only_text_is_a_rejection():
    client = _FakeVisionClient(text="   \n  \n")
    provider = GoogleVisionOcrProvider(client=client)
    result = provider.extract_text(b"fake image bytes")
    assert isinstance(result, OcrRejection)
    assert result.reason == OcrRejectionReason.NO_TEXT_DETECTED


def test_vendor_error_message_raises_ocr_provider_error():
    client = _FakeVisionClient(error_message="permission denied")
    provider = GoogleVisionOcrProvider(client=client)
    with pytest.raises(OcrProviderError):
        provider.extract_text(b"fake image bytes")


def test_transport_exception_raises_ocr_provider_error():
    client = _FakeVisionClient(exception=ConnectionError("network down"))
    provider = GoogleVisionOcrProvider(client=client)
    with pytest.raises(OcrProviderError):
        provider.extract_text(b"fake image bytes")
