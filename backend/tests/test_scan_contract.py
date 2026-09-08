import pytest
from pydantic import ValidationError

from app.contracts.scan_contract import (
    ScanResponse,
    ImageRejected,
    NutritionResult,
    UsdaSource,
    LabelSource,
    ScanError,
    RawFoodDetected
)

def test_image_rejected_valid():
    """Enum reasons must be validated exactly."""
    model = ImageRejected(status="image_rejected", reason="file_too_large")
    assert model.reason == "file_too_large"

def test_image_rejected_invalid_reason():
    """A bad reason should cause validation failure."""
    with pytest.raises(ValidationError):
        ImageRejected(status="image_rejected", reason="not_a_valid_reason")  # type: ignore

def test_raw_food_detected_candidates():
    """Lists should respect bounds and contain required data."""
    model = RawFoodDetected(
        status="raw_food_detected",
        food_name="Apple",
        suggested_quantity="1 medium (182g)",
        candidates=["Apple", "Pear"]
    )
    assert model.food_name == "Apple"

def test_nutrition_result_usda():
    """Nutrition result using USDA must pass validation."""
    model = NutritionResult(
        status="nutrition_result",
        food_name="Apple",
        calories=95.0,
        protein_g=0.5,
        carbs_g=25.0,
        fat_g=0.3,
        source=UsdaSource(type="usda", fdc_id="12345", usda_description="Apple, raw")
    )
    assert model.source.type == "usda"
    assert model.source.fdc_id == "12345"

def test_nutrition_result_label():
    """Nutrition result using Label must pass validation."""
    model = NutritionResult(
        status="nutrition_result",
        food_name="Granola Bar",
        calories=150.0,
        protein_g=3.0,
        carbs_g=20.0,
        fat_g=5.0,
        source=LabelSource(type="label", ocr_confidence=0.95)
    )
    assert model.source.type == "label"
    assert model.source.ocr_confidence == 0.95

def test_nutrition_result_cross_contamination():
    """NutritionSource prevents USDA source from having OCR confidence and vice versa."""
    with pytest.raises(ValidationError):
        UsdaSource(type="usda", fdc_id="12345", usda_description="Apple", ocr_confidence=0.9)  # type: ignore

    with pytest.raises(ValidationError):
        LabelSource(type="label", ocr_confidence=0.9, fdc_id="12345")  # type: ignore

def test_scan_error_retryable():
    """Errors require a retryable boolean."""
    model = ScanError(status="error", message="Network timeout", retryable=True)
    assert model.retryable is True

def test_extra_fields_forbidden():
    """All models must reject unknown fields due to extra='forbid'."""
    with pytest.raises(ValidationError):
        ScanError(status="error", message="Timeout", retryable=True, unknown_field="bad")  # type: ignore

def test_polymorphic_parsing():
    """The discriminated union parses correctly to the specific type."""
    from pydantic import TypeAdapter
    adapter = TypeAdapter(ScanResponse)
    
    data = {
        "status": "raw_food_detected",
        "food_name": "Banana",
        "suggested_quantity": "1 medium",
        "candidates": ["Banana", "Plantain"]
    }
    
    parsed = adapter.validate_python(data)
    assert isinstance(parsed, RawFoodDetected)
    assert parsed.food_name == "Banana"
