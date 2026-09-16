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
                    "page_size": 100,
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

        import re
        query_lowered = food_name.lower().strip()
        query_tokens = set(re.findall(r'[a-z]+', query_lowered))

        # Add basic plurals/singulars to allowed query tokens
        allowed_query_tokens = set(query_tokens)
        for t in query_tokens:
            if t.endswith('s'):
                allowed_query_tokens.add(t[:-1])
            else:
                allowed_query_tokens.add(t + 's')

        safe_modifiers = {"raw", "fresh", "organic", "whole", "natural", "unpeeled", "peeled"}
        valid_candidates = []

        for p in products:
            p_name = p.get("product_name", "").lower()
            if not p_name:
                continue

            p_tokens = set(re.findall(r'[a-z]+', p_name))

            # 1. Product must contain at least one of the core query tokens
            if not p_tokens.intersection(allowed_query_tokens):
                continue

            # 2. Every token in the product must be either in allowed_query_tokens or safe_modifiers
            is_strict_match = True
            for pt in p_tokens:
                if pt not in allowed_query_tokens and pt not in safe_modifiers:
                    is_strict_match = False
                    break

            if not is_strict_match:
                continue

            nutriments = p.get("nutriments")
            if not nutriments:
                continue

            # Must have core nutrients for raw food mapping
            if not ("energy-kcal_100g" in nutriments and "proteins_100g" in nutriments and "fat_100g" in nutriments and "carbohydrates_100g" in nutriments and "sugars_100g" in nutriments):
                continue

            # 3. Taxonomy validation and scoring
            nova = str(p.get("nova_group", "")).strip()
            if nova in {"3", "4"}:
                continue # Strong negative evidence

            pnns = str(p.get("pnns_groups_1", "")).lower()
            if "composite" in pnns or "snack" in pnns or "beverage" in pnns:
                continue # Strong negative evidence

            score = 0
            if nova == "1":
                score += 10

            tags = p.get("categories_tags", [])
            if isinstance(tags, list):
                raw_tags = {"en:fruits", "en:vegetables", "en:meats", "en:seafood", "en:nuts", "en:seeds", "en:legumes", "en:single-ingredient-food", "en:plant-based-foods-and-beverages", "en:plant-based-foods"}
                if any(t in raw_tags for t in tags):
                    score += 5

            valid_candidates.append((score, p))

        if valid_candidates:
            # Sort by score descending
            valid_candidates.sort(key=lambda x: x[0], reverse=True)
            best_candidate = valid_candidates[0][1]
            return DatabaseFoodMatch(
                db_id=best_candidate.get("_id", "unknown"),
                description=best_candidate.get("product_name", food_name),
                nutrients=_extract_nutrients(best_candidate.get("nutriments", {})),
            )

        return DatabaseLookupRejection(
            reason=DatabaseLookupReason.NO_MATCH,
            message=f"No strict match with nutrition data found for '{food_name}'.",
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
