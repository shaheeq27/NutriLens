import pytest
from app.providers.local_ocr import MockOcrProvider, OcrExtractionResult

def test_mock_provider_returns_canned_result_regardless_of_input():
    canned = OcrExtractionResult(raw_text_blocks=("Test",), provider_confidence=0.99)
    provider = MockOcrProvider(canned)
    assert provider.extract_text(b"anything") is canned
