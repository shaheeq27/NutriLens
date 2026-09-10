"""
Tests for backend/app/services/nutrition_lookup.py.
Run with: pytest test_nutrition_lookup.py -v
"""

import pytest

from app.services.nutrition_lookup import NutritionLookupOutcome, lookup_and_scale_nutrition
from app.providers.usda_fooddata import (
    MockNutritionLookupProvider,
    NutritionLookupError,
    UsdaFoodMatch,
    UsdaLookupReason,
    UsdaLookupRejection,
    UsdaNutrients,
)

# USDA's per-100g banana record (real values used elsewhere in this project).
_BANANA_PER_100G = UsdaNutrients(
    energy_kcal=89.0, protein_g=1.09, carbohydrates_g=22.8, fat_g=0.33,
    fiber_g=2.6, sugar_g=12.2, potassium_mg=358.0,
)


class _FailingProvider:
    def lookup_food(self, food_name: str):
        raise NutritionLookupError("simulated USDA outage")


def test_scaling_matches_hand_calculated_values_for_a_118g_banana():
    provider = MockNutritionLookupProvider(
        UsdaFoodMatch(fdc_id=1105073, description="Bananas, raw", nutrients=_BANANA_PER_100G)
    )
    result = lookup_and_scale_nutrition("banana", 118.0, provider)

    assert result.outcome == NutritionLookupOutcome.FOUND
    # 89 kcal/100g * 1.18 = 105.02
    assert result.nutrients.energy_kcal == 105.02
    # 1.09 g/100g * 1.18 = 1.2862 -> rounds to 1.29
    assert result.nutrients.protein_g == 1.29
    assert result.portion_grams == 118.0
    assert result.food_name == "Bananas, raw"
    assert result.fdc_id == 1105073


def test_scaling_at_exactly_100g_leaves_values_unchanged():
    provider = MockNutritionLookupProvider(
        UsdaFoodMatch(fdc_id=1, description="Test food", nutrients=_BANANA_PER_100G)
    )
    result = lookup_and_scale_nutrition("banana", 100.0, provider)
    assert result.nutrients.energy_kcal == 89.0
    assert result.nutrients.protein_g == 1.09


def test_missing_nutrient_fields_stay_none_after_scaling():
    """The banana fixture has no sodium/caffeine data — scaling must not
    turn a missing value into 0 or any other number."""
    provider = MockNutritionLookupProvider(
        UsdaFoodMatch(fdc_id=1, description="Bananas, raw", nutrients=_BANANA_PER_100G)
    )
    result = lookup_and_scale_nutrition("banana", 200.0, provider)
    assert result.nutrients.sodium_mg is None
    assert result.nutrients.caffeine_mg is None


def test_not_found_outcome():
    provider = MockNutritionLookupProvider(
        UsdaLookupRejection(reason=UsdaLookupReason.NO_MATCH, message="no match")
    )
    result = lookup_and_scale_nutrition("dragon fruit", 100.0, provider)
    assert result.outcome == NutritionLookupOutcome.NOT_FOUND
    assert result.nutrients is None


def test_provider_error_is_captured_not_raised():
    result = lookup_and_scale_nutrition("banana", 100.0, _FailingProvider())
    assert result.outcome == NutritionLookupOutcome.PROVIDER_ERROR
    assert "simulated USDA outage" in result.message


def test_zero_or_negative_portion_raises_value_error():
    provider = MockNutritionLookupProvider(
        UsdaFoodMatch(fdc_id=1, description="Test", nutrients=_BANANA_PER_100G)
    )
    with pytest.raises(ValueError):
        lookup_and_scale_nutrition("banana", 0, provider)
    with pytest.raises(ValueError):
        lookup_and_scale_nutrition("banana", -5, provider)
