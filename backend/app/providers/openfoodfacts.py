"""
NutriLens backend — Open Food Facts provider.

Looks up verified nutrition values for a confirmed raw-food name.
Replaces the old USDA FoodData Central provider with a 100% free API.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Protocol, Union, runtime_checkable

import httpx

BASE_URL = "https://world.openfoodfacts.org/cgi/search.pl"

class NutritionLookupError(Exception):
    """Raised when the provider fails outright — a network/API error."""

class DatabaseLookupReason(str, Enum):
    NO_MATCH = "no_match"

@dataclass(frozen=True)
class DatabaseNutrients:
    energy_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    carbohydrates_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    potassium_mg: Optional[float] = None
    caffeine_mg: Optional[float] = None

@dataclass(frozen=True)
class DatabaseFoodMatch:
    db_id: str
    description: str
    nutrients: DatabaseNutrients

@dataclass(frozen=True)
class DatabaseLookupRejection:
    reason: DatabaseLookupReason
    message: str

DatabaseLookupOutcome = Union[DatabaseFoodMatch, DatabaseLookupRejection]

@runtime_checkable
class NutritionLookupProvider(Protocol):
    def lookup_food(self, food_name: str) -> DatabaseLookupOutcome: ...

class MockNutritionLookupProvider:
    """Returns a fixed, caller-supplied outcome regardless of input food
    name — per the project's 'mock providers first' rule."""

    def __init__(self, canned_outcome: DatabaseLookupOutcome):
        self._canned_outcome = canned_outcome

    def lookup_food(self, food_name: str) -> DatabaseLookupOutcome:
        return self._canned_outcome

class OpenFoodFactsProvider:
    """Real implementation for Open Food Facts."""

    def __init__(self, http_client: Any = None, timeout_seconds: float = 10.0):
        # We set a proper User-Agent as required by Open Food Facts API guidelines
        headers = {"User-Agent": "NutriLens/1.0 - macOS - Local/Free Implementation"}
        self._client = http_client or httpx.Client(timeout=timeout_seconds, headers=headers)

    def lookup_food(self, food_name: str) -> DatabaseLookupOutcome:
        try:
            response = self._client.get(
                BASE_URL,
                params={
                    "search_terms": food_name,
                    "search_simple": 1,
                    "action": "process",
                    "json": 1,
                    "page_size": 20,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise NutritionLookupError(f"Open Food Facts request failed: {exc}") from exc

        data = response.json()
        products = data.get("products", [])
        if not products:
            return DatabaseLookupRejection(
                reason=DatabaseLookupReason.NO_MATCH,
                message=f"No verified record found in Open Food Facts for '{food_name}'.",
            )

        # Find the first product that has nutrition data and matches the raw food semantically
        query_lowered = food_name.lower().strip()
        disqualifiers = ["juice", "sauce", "flavored", "cake", "pie", "drink", "candy", "puree", "jam", "jelly", "powder", "syrup", "extract", "snack", "cracker", "crackers", "chips", "crisps"]

        for p in products:
            p_name = p.get("product_name", "").lower()
            if not p_name or query_lowered not in p_name:
                continue

            if any(dq in p_name for dq in disqualifiers):
                continue

            nutriments = p.get("nutriments")
            if not nutriments:
                continue

            # Must have core nutrients for raw food mapping
            if "energy-kcal_100g" in nutriments and "proteins_100g" in nutriments and "fat_100g" in nutriments and "carbohydrates_100g" in nutriments and "sugars_100g" in nutriments:
                return DatabaseFoodMatch(
                    db_id=p.get("_id", "unknown"),
                    description=p.get("product_name", food_name),
                    nutrients=_extract_nutrients(nutriments),
                )

        return DatabaseLookupRejection(
            reason=DatabaseLookupReason.NO_MATCH,
            message=f"Records found, but no nutrition data available for '{food_name}'.",
        )

def _extract_nutrients(nutriments: dict) -> DatabaseNutrients:
    # Open Food Facts returns per 100g as well as per serving.
    # We use per 100g to have a consistent baseline, or if it doesn't exist, we skip.

    def _get(key: str) -> float | None:
        val = nutriments.get(f"{key}_100g")
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    # sodium is usually provided in grams by OFF, but we might want mg
    sodium_g = _get("sodium")
    sodium_mg = (sodium_g * 1000) if sodium_g is not None else None

    return DatabaseNutrients(
        energy_kcal=_get("energy-kcal"),
        protein_g=_get("proteins"),
        carbohydrates_g=_get("carbohydrates"),
        fat_g=_get("fat"),
        fiber_g=_get("fiber"),
        sugar_g=_get("sugars"),
        sodium_mg=sodium_mg,
        potassium_mg=None, # OFF doesn't consistently expose potassium in the root nutriments usually
        caffeine_mg=None,
    )
