"""Tests for the scan contract schemas."""

from app.contracts.scan_contract import FoodType, NutrientInfo, ScanResponse


def test_scan_response_defaults():
    """ScanResponse should populate defaults for optional fields."""
    resp = ScanResponse(
        food_name="Apple",
        food_type=FoodType.RAW,
        confidence=0.95,
    )
    assert resp.food_name == "Apple"
    assert resp.food_type == FoodType.RAW
    assert resp.nutrients == []
    assert resp.ingredients == []
    assert resp.calories is None
    assert resp.serving_size is None


def test_nutrient_info():
    """NutrientInfo should hold nutrient details."""
    nutrient = NutrientInfo(
        name="Protein",
        amount=3.0,
        unit="g",
        daily_value_percent=6.0,
    )
    assert nutrient.name == "Protein"
    assert nutrient.amount == 3.0
    assert nutrient.unit == "g"
    assert nutrient.daily_value_percent == 6.0


def test_food_type_enum():
    """FoodType enum should have expected values."""
    assert FoodType.RAW == "raw"
    assert FoodType.PACKAGED == "packaged"
    assert FoodType.UNKNOWN == "unknown"
