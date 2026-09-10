"""
Tests for backend/app/services/label_ocr.py.
Run with: pytest test_label_ocr.py -v
"""

import io

import pytest
from PIL import Image

from app.providers.google_vision import MockOcrProvider, OcrProviderError, OcrRejection, OcrRejectionReason, OcrResult
from app.services.label_ocr import LabelExtractionOutcome, extract_label_nutrients, _parse_label_text


def _valid_jpeg(width=300, height=300) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(10, 20, 30)).save(buf, format="JPEG")
    return buf.getvalue()


REALISTIC_LABEL_TEXT = """
Nutrition Facts
Serving Size 30g
Calories 140
Total Fat 7g
Sodium 95mg
Total Carbohydrate 18g
Dietary Fiber 2g
Sugars 9g
Protein 2g
Potassium 120mg
"""


# ---------------------------------------------------------------------------
# _parse_label_text — the core regex extraction logic, tested directly
# ---------------------------------------------------------------------------

def test_realistic_label_extracts_all_present_fields():
    result = _parse_label_text(REALISTIC_LABEL_TEXT)
    assert result.outcome == LabelExtractionOutcome.EXTRACTED
    assert result.extracted["energy_kcal"] == 140
    assert result.extracted["fat_g"] == 7
    assert result.extracted["sodium_mg"] == 95
    assert result.extracted["carbohydrates_g"] == 18
    assert result.extracted["fiber_g"] == 2
    assert result.extracted["sugar_g"] == 9
    assert result.extracted["protein_g"] == 2
    assert result.extracted["potassium_mg"] == 120


def test_realistic_label_captures_serving_basis():
    result = _parse_label_text(REALISTIC_LABEL_TEXT)
    assert result.serving_basis == "Per 30g serving"


def test_realistic_label_reports_missing_fields_correctly():
    result = _parse_label_text(REALISTIC_LABEL_TEXT)
    assert "caffeine_mg" in result.missing_fields
    assert "energy_kcal" not in result.missing_fields


def test_energy_in_kcal_form_is_recognized():
    text = "Energy 350 kcal\nProtein 10g\nTotal Fat 5g\nTotal Carbohydrate 40g"
    result = _parse_label_text(text)
    assert result.extracted["energy_kcal"] == 350


def test_fat_without_total_prefix_is_recognized():
    text = "Calories 100\nFat 3g\nProtein 5g\nCarbohydrate 20g"
    result = _parse_label_text(text)
    assert result.extracted["fat_g"] == 3


def test_caffeine_is_recognized_for_beverages():
    text = "Calories 80\nProtein 0g\nTotal Fat 0g\nTotal Carbohydrate 22g\nCaffeine 32mg"
    result = _parse_label_text(text)
    assert result.extracted["caffeine_mg"] == 32


def test_no_serving_size_present_leaves_serving_basis_none():
    text = "Calories 100\nProtein 5g\nTotal Fat 2g\nTotal Carbohydrate 15g"
    result = _parse_label_text(text)
    assert result.serving_basis is None


def test_gibberish_text_with_no_nutrient_keywords_is_not_a_label():
    result = _parse_label_text("lorem ipsum dolor sit amet consectetur")
    assert result.outcome == LabelExtractionOutcome.NOT_A_NUTRITION_LABEL


def test_text_with_only_non_core_fields_is_not_a_label():
    """Sodium/potassium alone without any of the core four (calories,
    protein, carbs, fat) shouldn't count as a nutrition label — too
    likely to be an OCR fragment of something else entirely."""
    result = _parse_label_text("Sodium 50mg\nPotassium 100mg")
    assert result.outcome == LabelExtractionOutcome.NOT_A_NUTRITION_LABEL


def test_extraction_is_case_insensitive():
    text = "CALORIES 200\nPROTEIN 5G\nTOTAL FAT 10G\nTOTAL CARBOHYDRATE 25G"
    result = _parse_label_text(text)
    assert result.extracted["energy_kcal"] == 200
    assert result.extracted["fat_g"] == 10


# ---------------------------------------------------------------------------
# extract_label_nutrients — the full composed pipeline
# ---------------------------------------------------------------------------

def test_full_pipeline_success():
    provider = MockOcrProvider(OcrResult(raw_text=REALISTIC_LABEL_TEXT))
    result = extract_label_nutrients(_valid_jpeg(), provider)
    assert result.outcome == LabelExtractionOutcome.EXTRACTED
    assert result.extracted["energy_kcal"] == 140


def test_invalid_image_short_circuits_before_ocr():
    too_small = io.BytesIO()
    Image.new("RGB", (50, 50)).save(too_small, format="JPEG")

    class _FailingProvider:
        def extract_text(self, image_bytes):
            raise AssertionError("OCR should never be called for an invalid image")

    result = extract_label_nutrients(too_small.getvalue(), _FailingProvider())
    assert result.outcome == LabelExtractionOutcome.INVALID_IMAGE


def test_no_text_detected_rejection_maps_correctly():
    provider = MockOcrProvider(
        OcrRejection(reason=OcrRejectionReason.NO_TEXT_DETECTED, message="no text found")
    )
    result = extract_label_nutrients(_valid_jpeg(), provider)
    assert result.outcome == LabelExtractionOutcome.NO_TEXT_DETECTED


def test_provider_error_is_captured_not_raised():
    class _FailingProvider:
        def extract_text(self, image_bytes):
            raise OcrProviderError("simulated OCR outage")

    result = extract_label_nutrients(_valid_jpeg(), _FailingProvider())
    assert result.outcome == LabelExtractionOutcome.PROVIDER_ERROR
    assert "simulated OCR outage" in result.message


def test_ocr_success_but_not_a_label_maps_correctly():
    provider = MockOcrProvider(OcrResult(raw_text="just some random receipt text"))
    result = extract_label_nutrients(_valid_jpeg(), provider)
    assert result.outcome == LabelExtractionOutcome.NOT_A_NUTRITION_LABEL
