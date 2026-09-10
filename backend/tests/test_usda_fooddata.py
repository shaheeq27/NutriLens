"""
Tests for backend/app/providers/usda_fooddata.py.
Run with: pytest test_usda_fooddata.py -v

Uses httpx.MockTransport rather than a hand-rolled fake client — this
exercises the real httpx.Client request-building and response-parsing
code path (URL construction, query param serialization) while only
stubbing the actual network layer. No real API key or network access
is used anywhere here.
"""

import httpx
import pytest

from app.providers.usda_fooddata import (
    MockNutritionLookupProvider,
    NutritionLookupError,
    UsdaFoodDataProvider,
    UsdaFoodMatch,
    UsdaLookupReason,
    UsdaLookupRejection,
    UsdaNutrients,
    _extract_nutrients,
)


def _client_with_handler(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.nal.usda.gov/fdc/v1")


BANANA_SEARCH_RESPONSE = {
    "foodSearchCriteria": {"query": "banana"},
    "totalHits": 1,
    "currentPage": 1,
    "totalPages": 1,
    "foods": [
        {
            "fdcId": 1105073,
            "description": "Bananas, raw",
            "dataType": "Foundation",
            "foodNutrients": [
                {"number": 208, "name": "Energy", "amount": 89.0, "unitName": "kcal"},
                {"number": 203, "name": "Protein", "amount": 1.09, "unitName": "g"},
                {"number": 205, "name": "Carbohydrate, by difference", "amount": 22.8, "unitName": "g"},
                {"number": 204, "name": "Total lipid (fat)", "amount": 0.33, "unitName": "g"},
                {"number": 291, "name": "Fiber, total dietary", "amount": 2.6, "unitName": "g"},
                {"number": 269, "name": "Sugars, total", "amount": 12.2, "unitName": "g"},
                {"number": 306, "name": "Potassium, K", "amount": 358.0, "unitName": "mg"},
                # Deliberately no sodium/caffeine entries — real foods often
                # omit nutrients that weren't measured for that record.
            ],
        }
    ],
}


# ---------------------------------------------------------------------------
# MockNutritionLookupProvider
# ---------------------------------------------------------------------------

def test_mock_provider_returns_canned_outcome_regardless_of_input():
    canned = UsdaFoodMatch(fdc_id=1, description="Test food", nutrients=UsdaNutrients())
    provider = MockNutritionLookupProvider(canned)
    assert provider.lookup_food("anything") is canned
    assert provider.lookup_food("") is canned


# ---------------------------------------------------------------------------
# _extract_nutrients — pure function, the core mapping logic
# ---------------------------------------------------------------------------

def test_extract_nutrients_maps_known_numbers_correctly():
    result = _extract_nutrients(BANANA_SEARCH_RESPONSE["foods"][0]["foodNutrients"])
    assert result.energy_kcal == 89.0
    assert result.protein_g == 1.09
    assert result.carbohydrates_g == 22.8
    assert result.fat_g == 0.33
    assert result.fiber_g == 2.6
    assert result.sugar_g == 12.2
    assert result.potassium_mg == 358.0


def test_extract_nutrients_leaves_missing_fields_none():
    result = _extract_nutrients(BANANA_SEARCH_RESPONSE["foods"][0]["foodNutrients"])
    assert result.sodium_mg is None
    assert result.caffeine_mg is None


def test_extract_nutrients_ignores_unmapped_nutrient_numbers():
    entries = [{"number": 999999, "name": "Some obscure nutrient", "amount": 5.0, "unitName": "g"}]
    result = _extract_nutrients(entries)
    assert result == UsdaNutrients()  # nothing mapped, all fields stay None


def test_extract_nutrients_handles_string_typed_numbers_too():
    """The OpenAPI spec types `number` as integer, but real-world API
    responses have been observed with it as a string in some contexts —
    this should not silently drop the value either way."""
    entries = [{"number": "208", "amount": 100.0, "unitName": "kcal"}]
    result = _extract_nutrients(entries)
    assert result.energy_kcal == 100.0


# ---------------------------------------------------------------------------
# UsdaFoodDataProvider — full request/response cycle via MockTransport
# ---------------------------------------------------------------------------

def test_successful_lookup_returns_match_with_mapped_nutrients():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BANANA_SEARCH_RESPONSE)

    provider = UsdaFoodDataProvider(api_key="fake", http_client=_client_with_handler(handler))
    result = provider.lookup_food("banana")

    assert isinstance(result, UsdaFoodMatch)
    assert result.fdc_id == 1105073
    assert result.description == "Bananas, raw"
    assert result.nutrients.energy_kcal == 89.0


def test_request_includes_api_key_query_and_restricted_data_types():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=BANANA_SEARCH_RESPONSE)

    provider = UsdaFoodDataProvider(api_key="MY_KEY", http_client=_client_with_handler(handler))
    provider.lookup_food("banana")

    assert "api_key=MY_KEY" in captured["url"]
    assert "query=banana" in captured["url"]
    assert "dataType=Foundation" in captured["url"]
    assert "dataType=SR" in captured["url"]  # "SR Legacy", URL-encoded


def test_no_results_returns_rejection_not_an_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "foodSearchCriteria": {}, "totalHits": 0, "currentPage": 1, "totalPages": 0, "foods": [],
        })

    provider = UsdaFoodDataProvider(api_key="fake", http_client=_client_with_handler(handler))
    result = provider.lookup_food("a food that doesn't exist")

    assert isinstance(result, UsdaLookupRejection)
    assert result.reason == UsdaLookupReason.NO_MATCH


def test_http_error_status_raises_nutrition_lookup_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "invalid api key"}})

    provider = UsdaFoodDataProvider(api_key="bad-key", http_client=_client_with_handler(handler))
    with pytest.raises(NutritionLookupError):
        provider.lookup_food("banana")


def test_rate_limit_status_raises_nutrition_lookup_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limited"})

    provider = UsdaFoodDataProvider(api_key="fake", http_client=_client_with_handler(handler))
    with pytest.raises(NutritionLookupError):
        provider.lookup_food("banana")


def test_connection_error_raises_nutrition_lookup_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = UsdaFoodDataProvider(api_key="fake", http_client=_client_with_handler(handler))
    with pytest.raises(NutritionLookupError):
        provider.lookup_food("banana")
