import io
import pytest
from PIL import Image

from app.providers.local_ocr import MockOcrProvider, OcrProviderError, OcrExtractionResult
from app.services.label_ocr import LabelExtractionOutcome, extract_label_nutrients, _parse_label_text

REALISTIC_LABEL_TEXT = "Calories 140\nProtein 2g\nTotal Fat 7g\nTotal Carbohydrate 18g\nTotal Sugars 12g\nSodium 90mg"

def _valid_jpeg(width=300, height=300) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color="white").save(buf, format="JPEG")
    return buf.getvalue()

def test_full_pipeline_success():
    provider = MockOcrProvider(OcrExtractionResult(raw_text_blocks=tuple(REALISTIC_LABEL_TEXT.split("\n")), provider_confidence=0.9))
    result = extract_label_nutrients(_valid_jpeg(), provider)
    assert result.outcome == LabelExtractionOutcome.EXTRACTED
    assert result.extracted["energy_kcal"] == 140

def test_no_text_detected_rejection_maps_correctly():
    provider = MockOcrProvider(
        OcrExtractionResult(raw_text_blocks=(), provider_confidence=0.0)
    )
    result = extract_label_nutrients(_valid_jpeg(), provider)
    assert result.outcome == LabelExtractionOutcome.NO_TEXT_DETECTED

def test_provider_error_is_caught_and_mapped():
    class _FailingProvider:
        def extract_text(self, image_bytes):
            raise OcrProviderError("simulated OCR outage")

    result = extract_label_nutrients(_valid_jpeg(), _FailingProvider())
    assert result.outcome == LabelExtractionOutcome.PROVIDER_ERROR
    assert "simulated OCR outage" in result.message

def test_ocr_success_but_not_a_label_maps_correctly():
    provider = MockOcrProvider(OcrExtractionResult(raw_text_blocks=("just some random receipt text",), provider_confidence=0.9))
    result = extract_label_nutrients(_valid_jpeg(), provider)
    assert result.outcome == LabelExtractionOutcome.NOT_A_NUTRITION_LABEL

def test_missing_core_nutrients_rejection():
    # Only calories and protein
    text = "Calories 140\nProtein 2g"
    provider = MockOcrProvider(OcrExtractionResult(raw_text_blocks=tuple(text.split("\n")), provider_confidence=0.9))
    result = extract_label_nutrients(_valid_jpeg(), provider)
    assert result.outcome == LabelExtractionOutcome.EXTRACTED
    assert "fat_g" not in result.extracted

def test_malformed_numeric_values_rejected_or_treated_as_missing():
    # Fat is unparseable
    text = "Calories 140\nProtein 2g\nTotal Fat O.O\nTotal Carbohydrate 18g\nTotal Sugars 12g"
    provider = MockOcrProvider(OcrExtractionResult(raw_text_blocks=tuple(text.split("\n")), provider_confidence=0.9))
    result = extract_label_nutrients(_valid_jpeg(), provider)
    # Since fat is a core nutrient and unparseable, it treats it as missing
    assert result.outcome == LabelExtractionOutcome.EXTRACTED
    assert "fat_g" not in result.extracted

def test_no_zero_fabrication_for_missing_optional_fields():
    # Provide all core nutrients (calories, protein, fat, carbs, sugar)
    text = "Calories 140\nProtein 2g\nTotal Fat 7g\nTotal Carbohydrate 18g\nTotal Sugars 12g"
    provider = MockOcrProvider(OcrExtractionResult(raw_text_blocks=tuple(text.split("\n")), provider_confidence=0.9))
    result = extract_label_nutrients(_valid_jpeg(), provider)
    assert result.outcome == LabelExtractionOutcome.EXTRACTED
    # Optional field like sodium should not be 0.0, it should be absent
    assert "sodium_mg" not in result.extracted
    assert "fiber_g" not in result.extracted
