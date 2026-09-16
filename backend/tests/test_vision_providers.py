import pytest
import httpx
from app.providers.vision import (
    VisionManager, VisionRecognitionResult, DetectionOutcome,
    VisionProviderError, VisionProviderRecoverableError, VisionProviderAuthError
)
from app.providers.gemini_vision import GeminiVisionProvider
from app.providers.openrouter_vision import OpenRouterVisionProvider

class MockHttpxResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code
    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)
    @property
    def text(self):
        import json
        return json.dumps(self._json_data)

    def json(self):
        return self._json_data

class MockHttpxClient:
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0
        self.last_url = None
        self.last_payload = None
    def post(self, url, **kwargs):
        self.call_count += 1
        self.last_url = url
        if "json" in kwargs:
            self.last_payload = kwargs["json"]
        if isinstance(self.responses, list):
            res = self.responses.pop(0)
            if isinstance(res, Exception):
                raise res
            return res
        if isinstance(self.responses, Exception):
            raise self.responses
        return self.responses

def test_gemini_successful_recognition():
    client = MockHttpxClient(MockHttpxResponse({
        "candidates": [{"content": {"parts": [{"text": '{"outcome": "RAW_FOOD", "food_name": "apple"}'}]}}]
    }))
    provider = GeminiVisionProvider(api_key="test", http_client=client)
    res = provider.recognize_food(b"test")
    assert res.outcome == DetectionOutcome.RAW_FOOD
    assert res.food_name == "apple"
    assert "gemini-3.8-flash" in client.last_url

def test_gemini_429_openrouter_fallback(monkeypatch):
    monkeypatch.setattr('time.sleep', lambda x: None)
    gemini_client = MockHttpxClient(MockHttpxResponse({}, status_code=429))
    gemini = GeminiVisionProvider(api_key="test", http_client=gemini_client)

    or_client = MockHttpxClient(MockHttpxResponse({
        "choices": [{"message": {"content": '{"outcome": "PACKAGE", "product_guess": "snack"}'}}]
    }))
    openrouter = OpenRouterVisionProvider(api_key="test", http_client=or_client)

    manager = VisionManager(primary=gemini, fallback=openrouter)
    res = manager.recognize_food(b"test")
    assert res.outcome == DetectionOutcome.PACKAGE
    assert res.product_guess == "snack"
    assert gemini_client.call_count == 1
    assert or_client.call_count == 1
    assert or_client.last_payload["model"] == "google/gemma-4-31b-it:free"

def test_gemini_timeout_openrouter_fallback(monkeypatch):
    monkeypatch.setattr('time.sleep', lambda x: None)
    gemini_client = MockHttpxClient(httpx.TimeoutException("timeout"))
    gemini = GeminiVisionProvider(api_key="test", http_client=gemini_client)

    or_client = MockHttpxClient(MockHttpxResponse({
        "choices": [{"message": {"content": '{"outcome": "RAW_FOOD", "food_name": "banana"}'}}]
    }))
    openrouter = OpenRouterVisionProvider(api_key="test", http_client=or_client)

    manager = VisionManager(primary=gemini, fallback=openrouter)
    res = manager.recognize_food(b"test")
    assert res.outcome == DetectionOutcome.RAW_FOOD
    assert gemini_client.call_count == 1
    assert or_client.call_count == 1

def test_gemini_auth_error_no_fallback():
    gemini_client = MockHttpxClient(MockHttpxResponse({}, status_code=401))
    gemini = GeminiVisionProvider(api_key="test", http_client=gemini_client)

    or_client = MockHttpxClient(MockHttpxResponse({
        "choices": [{"message": {"content": '{"outcome": "RAW_FOOD"}'}}]
    }))
    openrouter = OpenRouterVisionProvider(api_key="test", http_client=or_client)

    manager = VisionManager(primary=gemini, fallback=openrouter)
    with pytest.raises(VisionProviderAuthError):
        manager.recognize_food(b"test")
    assert gemini_client.call_count == 1
    assert or_client.call_count == 0

def test_both_providers_failing(monkeypatch):
    monkeypatch.setattr('time.sleep', lambda x: None)
    gemini_client = MockHttpxClient(MockHttpxResponse({}, status_code=500))
    gemini = GeminiVisionProvider(api_key="test", http_client=gemini_client)

    or_client = MockHttpxClient(httpx.NetworkError("network error"))
    openrouter = OpenRouterVisionProvider(api_key="test", http_client=or_client)

    manager = VisionManager(primary=gemini, fallback=openrouter)
    with pytest.raises(VisionProviderRecoverableError):
        manager.recognize_food(b"test")
    assert gemini_client.call_count == 1
    assert or_client.call_count == 1

def test_logo_non_food_image():
    client = MockHttpxClient(MockHttpxResponse({
        "candidates": [{"content": {"parts": [{"text": '{"outcome": "NO_FOOD_DETECTED"}'}]}}]
    }))
    provider = GeminiVisionProvider(api_key="test", http_client=client)
    res = provider.recognize_food(b"test")
    assert res.outcome == DetectionOutcome.NO_FOOD_DETECTED

def test_ambiguous_image():
    client = MockHttpxClient(MockHttpxResponse({
        "candidates": [{"content": {"parts": [{"text": '{"outcome": "LOW_CONFIDENCE"}'}]}}]
    }))
    provider = GeminiVisionProvider(api_key="test", http_client=client)
    res = provider.recognize_food(b"test")
    assert res.outcome == DetectionOutcome.LOW_CONFIDENCE

def test_fabricated_nutrition_ignored():
    client = MockHttpxClient(MockHttpxResponse({
        "candidates": [{"content": {"parts": [{"text": '{"outcome": "RAW_FOOD", "food_name": "apple", "calories": 50, "protein": 1}'}]}}]
    }))
    provider = GeminiVisionProvider(api_key="test", http_client=client)
    res = provider.recognize_food(b"test")
    assert res.outcome == DetectionOutcome.RAW_FOOD
    assert res.food_name == "apple"
    assert not hasattr(res, "calories")

def test_gemini_503_immediate_fallback(monkeypatch):
    monkeypatch.setattr('time.sleep', lambda x: None)
    gemini_client = MockHttpxClient(MockHttpxResponse({}, status_code=503))
    gemini = GeminiVisionProvider(api_key="test", http_client=gemini_client)

    or_client = MockHttpxClient(MockHttpxResponse({
        "choices": [{"message": {"content": '{"outcome": "PACKAGE", "product_guess": "snack"}'}}]
    }))
    openrouter = OpenRouterVisionProvider(api_key="test", http_client=or_client)

    manager = VisionManager(primary=gemini, fallback=openrouter)
    res = manager.recognize_food(b"test")
    assert res.outcome == DetectionOutcome.PACKAGE
    assert gemini_client.call_count == 1
    assert or_client.call_count == 1
