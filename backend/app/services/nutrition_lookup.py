"""Nutrition lookup service — fetches detailed nutritional data for identified foods."""

from app.contracts.scan_contract import NutrientInfo


async def lookup_nutrition(food_name: str) -> dict:
    """
    Look up nutritional information for a given food name.

    Returns a dict with:
      - calories: float | None
      - nutrients: list[NutrientInfo]
    """
    # TODO: Integrate with a nutrition database or AI-based extraction
    return {
        "calories": None,
        "nutrients": [],
    }
