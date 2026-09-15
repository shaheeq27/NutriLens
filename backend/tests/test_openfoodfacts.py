import pytest
import httpx
from app.providers.openfoodfacts import (
    MockNutritionLookupProvider, OpenFoodFactsProvider,
    DatabaseFoodMatch, DatabaseNutrients, DatabaseLookupRejection, DatabaseLookupReason, NutritionLookupError
)

class MockHttpxResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code
    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)
    def json(self):
        return self._json_data

class MockHttpxClient:
    def __init__(self, responses):
        self.responses = responses
    def get(self, url, params=None, **kwargs):
        if isinstance(self.responses, Exception):
            raise self.responses
        return self.responses

def test_off_provider_empty_products_no_match():
    client = MockHttpxClient(MockHttpxResponse({"products": []}))
    provider = OpenFoodFactsProvider(http_client=client)
    res = provider.lookup_food("apple")
    assert isinstance(res, DatabaseLookupRejection)
    assert res.reason == DatabaseLookupReason.NO_MATCH
    assert res.reason == DatabaseLookupReason.NO_MATCH

def test_off_provider_products_without_nutrition_no_match():
    client = MockHttpxClient(MockHttpxResponse({"products": [{"product_name": "apple", "nutriments": {}}]}))
    provider = OpenFoodFactsProvider(http_client=client)
    res = provider.lookup_food("apple")
    assert isinstance(res, DatabaseLookupRejection)
    assert res.reason == DatabaseLookupReason.NO_MATCH
    assert res.reason == DatabaseLookupReason.NO_MATCH

def test_off_provider_valid_product():
    client = MockHttpxClient(MockHttpxResponse({
        "products": [{
            "_id": "0001",
            "product_name": "Fresh Apple",
            "nutriments": {
                "energy-kcal_100g": 52,
                "proteins_100g": 0.3,
                "fat_100g": 0.2,
                "carbohydrates_100g": 14,
                "sugars_100g": 10
            }
        }]
    }))
    provider = OpenFoodFactsProvider(http_client=client)
    res = provider.lookup_food("apple")
    assert isinstance(res, DatabaseFoodMatch)
    assert res.db_id == "0001"
    assert res.nutrients.energy_kcal == 52.0
    assert res.nutrients.sugar_g == 10.0

def test_off_provider_malformed_nutrient_values_nullable():
    client = MockHttpxClient(MockHttpxResponse({
        "products": [{
            "_id": "0002",
            "product_name": "Apple",
            "nutriments": {
                "energy-kcal_100g": "hello", # malformed
                "proteins_100g": 0.3,
                "fat_100g": 0.2,
                "carbohydrates_100g": 14,
                "sugars_100g": None
            }
        }]
    }))
    provider = OpenFoodFactsProvider(http_client=client)
    res = provider.lookup_food("apple")
    # Will fail the core nutrient check and skip to rejection
    assert isinstance(res, DatabaseFoodMatch)
    assert res.nutrients.energy_kcal is None

def test_off_provider_http_error():
    client = MockHttpxClient(httpx.RequestError("Network error"))
    provider = OpenFoodFactsProvider(http_client=client)
    with pytest.raises(NutritionLookupError):
        provider.lookup_food("apple")


def test_off_provider_rejects_false_semantic_matches():
    # If looking for "apple", and it returns "apple juice" with full nutrition, it should be rejected.
    client = MockHttpxClient(MockHttpxResponse({
        "products": [{
            "_id": "0003",
            "product_name": "Apple Juice",
            "nutriments": {
                "energy-kcal_100g": 50,
                "proteins_100g": 0.1,
                "fat_100g": 0.1,
                "carbohydrates_100g": 12,
                "sugars_100g": 11
            }
        }]
    }))
    provider = OpenFoodFactsProvider(http_client=client)
    res = provider.lookup_food("apple")
    assert isinstance(res, DatabaseLookupRejection)
    assert res.reason == DatabaseLookupReason.NO_MATCH
