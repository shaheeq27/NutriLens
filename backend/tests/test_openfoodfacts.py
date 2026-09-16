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

def test_off_provider_strict_matching_banana():
    base_nutriments = {
        "energy-kcal_100g": 89,
        "proteins_100g": 1.1,
        "fat_100g": 0.3,
        "carbohydrates_100g": 22.8,
        "sugars_100g": 12.2
    }

    def make_client(p_name):
        return MockHttpxClient(MockHttpxResponse({
            "products": [{
                "_id": "0001",
                "product_name": p_name,
                "nutriments": base_nutriments
            }]
        }))

    # Accepted matches
    for valid_name in ["banana", "raw banana", "banana, raw", "fresh bananas", "organic banana"]:
        provider = OpenFoodFactsProvider(http_client=make_client(valid_name))
        res = provider.lookup_food("banana")
        assert isinstance(res, DatabaseFoodMatch), f"Expected '{valid_name}' to match 'banana'"

    # Rejected matches
    for invalid_name in ["yogurt brine banana", "banana cake", "banana chips", "banana drink", "banana yogurt", "chocolate banana"]:
        provider = OpenFoodFactsProvider(http_client=make_client(invalid_name))
        res = provider.lookup_food("banana")
        assert isinstance(res, DatabaseLookupRejection), f"Expected '{invalid_name}' to be rejected for 'banana'"
        assert res.reason == DatabaseLookupReason.NO_MATCH

def test_off_provider_never_select_first_arbitrary_candidate():
    base_nutriments = {
        "energy-kcal_100g": 89,
        "proteins_100g": 1.1,
        "fat_100g": 0.3,
        "carbohydrates_100g": 22.8,
        "sugars_100g": 12.2
    }

    client = MockHttpxClient(MockHttpxResponse({
        "products": [
            {
                "_id": "0001",
                "product_name": "yogurt brine banana",
                "nutriments": base_nutriments
            },
            {
                "_id": "0002",
                "product_name": "banana cake",
                "nutriments": base_nutriments
            },
            {
                "_id": "0003",
                "product_name": "raw banana",
                "nutriments": base_nutriments
            }
        ]
    }))

    provider = OpenFoodFactsProvider(http_client=client)
    res = provider.lookup_food("banana")

    assert isinstance(res, DatabaseFoodMatch)
    # It should skip the first two and match the third
    assert res.db_id == "0003"
    assert res.description == "raw banana"

def test_off_provider_ranking():
    base_nutriments = {
        "energy-kcal_100g": 89,
        "proteins_100g": 1.1,
        "fat_100g": 0.3,
        "carbohydrates_100g": 22.8,
        "sugars_100g": 12.2
    }

    # 3 candidates:
    # 1. Huel (strict name, but NOVA 4 -> rejected)
    # 2. Raw banana with missing nova but has tags (score 5)
    # 3. Raw banana with nova 1 and tags (score 15)

    client = MockHttpxClient(MockHttpxResponse({
        "products": [
            {
                "_id": "0001",
                "product_name": "banana",
                "nova_group": 4,
                "pnns_groups_1": "Composite foods",
                "nutriments": base_nutriments
            },
            {
                "_id": "0002",
                "product_name": "banana",
                "nova_group": None,
                "categories_tags": ["en:fruits"],
                "nutriments": base_nutriments
            },
            {
                "_id": "0003",
                "product_name": "banana",
                "nova_group": 1,
                "categories_tags": ["en:fruits"],
                "nutriments": base_nutriments
            }
        ]
    }))

    provider = OpenFoodFactsProvider(http_client=client)
    res = provider.lookup_food("banana")

    assert isinstance(res, DatabaseFoodMatch)
    assert res.db_id == "0003"  # Because it has the highest score (15 vs 5)

def test_off_provider_reject_bad_taxonomy():
    base_nutriments = {
        "energy-kcal_100g": 89,
        "proteins_100g": 1.1,
        "fat_100g": 0.3,
        "carbohydrates_100g": 22.8,
        "sugars_100g": 12.2
    }

    client = MockHttpxClient(MockHttpxResponse({
        "products": [
            {
                "_id": "0001",
                "product_name": "banana",
                "nova_group": 4,
                "pnns_groups_1": "Composite foods",
                "nutriments": base_nutriments
            }
        ]
    }))

    provider = OpenFoodFactsProvider(http_client=client)
    res = provider.lookup_food("banana")

    assert isinstance(res, DatabaseLookupRejection)
