"""
NutriLens backend — USDA FoodData Central provider.

Looks up verified nutrition values for a confirmed raw-food name. This is
the ONLY source of nutrition numbers for the raw-food path — the vision
model in openai_vision.py identifies the food, but never estimates its
nutrition; this provider supplies the real numbers, or reports no match.

No official Python SDK exists for FoodData Central (it's a plain REST
API), so this uses httpx directly. The endpoint shape and field names
(`foods`, `fdcId`, `description`, `foodNutrients[].number`/`.amount`)
were verified against the live API guide
(https://fdc.nal.usda.gov/api-guide/) and the published OpenAPI spec
directly, not assumed from memory.

Nutrient number -> field mapping (USDA's stable numeric nutrient codes,
independent of any particular API version, cross-checked against
official USDA/Health Canada nutrient code listings):
  208 = Energy (kcal)     203 = Protein (g)      205 = Carbohydrate (g)
  204 = Fat (g)           291 = Fiber (g)        269 = Sugars, total (g)
  307 = Sodium (mg)       306 = Potassium (mg)   262 = Caffeine (mg)

Search is restricted to dataType=["Foundation", "SR Legacy"] — the
generic/reference entries (e.g. "Bananas, raw"), not Branded products,
which is the correct universe for the raw-food flow specifically.

Deliberately self-contained, same reasoning as the other Lane B provider
files: no import from app.contracts.scan_contract (still unresolved),
and the API key is a constructor parameter, not an environment read —
no dependency on the .env.example naming conflict.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Protocol, Union, runtime_checkable

import httpx

BASE_URL = "https://api.nal.usda.gov/fdc/v1"

_NUTRIENT_NUMBER_MAP: dict[str, str] = {
    "208": "energy_kcal",
    "203": "protein_g",
    "205": "carbohydrates_g",
    "204": "fat_g",
    "291": "fiber_g",
    "269": "sugar_g",
    "307": "sodium_mg",
    "306": "potassium_mg",
    "262": "caffeine_mg",
}


class NutritionLookupError(Exception):
    """Raised when the provider fails outright — a network/API error,
    not a 'no match found' business outcome (that's a normal return
    value, UsdaLookupRejection)."""


class UsdaLookupReason(str, Enum):
    NO_MATCH = "no_match"


@dataclass(frozen=True)
class UsdaNutrients:
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
class UsdaFoodMatch:
    fdc_id: int
    description: str
    nutrients: UsdaNutrients


@dataclass(frozen=True)
class UsdaLookupRejection:
    reason: UsdaLookupReason
    message: str


UsdaLookupOutcome = Union[UsdaFoodMatch, UsdaLookupRejection]


@runtime_checkable
class NutritionLookupProvider(Protocol):
    def lookup_food(self, food_name: str) -> UsdaLookupOutcome: ...


class MockNutritionLookupProvider:
    """Returns a fixed, caller-supplied outcome regardless of input food
    name — per the project's 'mock providers first' rule."""

    def __init__(self, canned_outcome: UsdaLookupOutcome):
        self._canned_outcome = canned_outcome

    def lookup_food(self, food_name: str) -> UsdaLookupOutcome:
        return self._canned_outcome


class UsdaFoodDataProvider:
    """Real implementation. `http_client` can be injected for testing —
    see test_usda_fooddata.py, which never touches the network."""

    def __init__(self, api_key: str, http_client: Any = None, timeout_seconds: float = 10.0):
        self._api_key = api_key
        self._client = http_client or httpx.Client(base_url=BASE_URL, timeout=timeout_seconds)

    def lookup_food(self, food_name: str) -> UsdaLookupOutcome:
        try:
            response = self._client.get(
                "/foods/search",
                params={
                    "api_key": self._api_key,
                    "query": food_name,
                    "pageSize": 1,
                    "dataType": ["Foundation", "SR Legacy"],
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise NutritionLookupError(f"USDA FoodData Central request failed: {exc}") from exc

        data = response.json()
        foods = data.get("foods", [])
        if not foods:
            return UsdaLookupRejection(
                reason=UsdaLookupReason.NO_MATCH,
                message=f"No verified USDA record found for '{food_name}'.",
            )

        top = foods[0]
        return UsdaFoodMatch(
            fdc_id=top["fdcId"],
            description=top["description"],
            nutrients=_extract_nutrients(top.get("foodNutrients", [])),
        )


def _extract_nutrients(food_nutrients: list[dict]) -> UsdaNutrients:
    values: dict[str, float] = {}
    for entry in food_nutrients:
        number = entry.get("number")
        amount = entry.get("amount")
        if number is None or amount is None:
            continue
        field_name = _NUTRIENT_NUMBER_MAP.get(str(number))
        if field_name is not None:
            values[field_name] = amount
    return UsdaNutrients(**values)