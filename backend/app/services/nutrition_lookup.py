"""
NutriLens backend — nutrition lookup service.

Composes the USDA provider with the one bit of real logic on top of it:
USDA nutrient values are per 100g, but the user confirms an actual
portion in grams — this module scales the looked-up values to that
confirmed amount. It does not call any vision/OCR provider and does not
touch the packaged-food path at all.

Deliberately self-contained: no import from app.contracts.scan_contract
(still unresolved), no environment reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from usda_fooddata import (
    NutritionLookupError,
    NutritionLookupProvider,
    UsdaFoodMatch,
    UsdaLookupRejection,
    UsdaNutrients,
)

# USDA FoodData Central nutrient values (Foundation / SR Legacy data
# types, which this provider restricts to) are reported per 100g.
_USDA_REFERENCE_GRAMS = 100.0


class NutritionLookupOutcome(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    PROVIDER_ERROR = "provider_error"


@dataclass(frozen=True)
class ScaledNutritionResult:
    outcome: NutritionLookupOutcome
    food_name: Optional[str] = None
    fdc_id: Optional[int] = None
    portion_grams: Optional[float] = None
    nutrients: Optional[UsdaNutrients] = None
    message: Optional[str] = None


def lookup_and_scale_nutrition(
    food_name: str, portion_grams: float, provider: NutritionLookupProvider
) -> ScaledNutritionResult:
    """The actual composed step: look up the food, then scale its
    per-100g nutrient values to the confirmed portion."""
    if portion_grams <= 0:
        raise ValueError("portion_grams must be positive")

    try:
        outcome = provider.lookup_food(food_name)
    except NutritionLookupError as exc:
        return ScaledNutritionResult(outcome=NutritionLookupOutcome.PROVIDER_ERROR, message=str(exc))

    if isinstance(outcome, UsdaLookupRejection):
        return ScaledNutritionResult(outcome=NutritionLookupOutcome.NOT_FOUND, message=outcome.message)

    scaled = _scale_nutrients(outcome.nutrients, portion_grams)
    return ScaledNutritionResult(
        outcome=NutritionLookupOutcome.FOUND,
        food_name=outcome.description,
        fdc_id=outcome.fdc_id,
        portion_grams=portion_grams,
        nutrients=scaled,
    )


def _scale_nutrients(nutrients: UsdaNutrients, portion_grams: float) -> UsdaNutrients:
    factor = portion_grams / _USDA_REFERENCE_GRAMS
    return UsdaNutrients(
        energy_kcal=_scale(nutrients.energy_kcal, factor),
        protein_g=_scale(nutrients.protein_g, factor),
        carbohydrates_g=_scale(nutrients.carbohydrates_g, factor),
        fat_g=_scale(nutrients.fat_g, factor),
        fiber_g=_scale(nutrients.fiber_g, factor),
        sugar_g=_scale(nutrients.sugar_g, factor),
        sodium_mg=_scale(nutrients.sodium_mg, factor),
        potassium_mg=_scale(nutrients.potassium_mg, factor),
        caffeine_mg=_scale(nutrients.caffeine_mg, factor),
    )


def _scale(value: Optional[float], factor: float) -> Optional[float]:
    return None if value is None else round(value * factor, 2)