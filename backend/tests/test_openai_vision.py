"""
Tests for backend/app/providers/openai_vision.py.
Run with: pytest test_openai_vision.py -v

No real OpenAI API key or network access is used anywhere here — the
client is always a fake/stub injected via the `client=` constructor
parameter, exercising OpenAIVisionProvider's request-building and
response-parsing logic in isolation.
"""

import json

import pytest

from app.providers.openai_vision import (
    DetectionOutcome,
    MockVisionProvider,
    OpenAIVisionProvider,
    VisionProviderError,
    VisionRecognitionResult,
    _JSON_SCHEMA,
)


# ---------------------------------------------------------------------------
# Fake OpenAI client — duck-types just enough of the real SDK shape
# ---------------------------------------------------------------------------

class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content=None, exception=None):
        self._content = content
        self._exception = exception
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        if self._exception is not None:
            raise self._exception
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeOpenAIClient:
    def __init__(self, content=None, exception=None):
        self.completions = _FakeCompletions(content, exception)
        self.chat = _FakeChat(self.completions)


def _client_returning(payload: dict) -> _FakeOpenAIClient:
    return _FakeOpenAIClient(content=json.dumps(payload))


# ---------------------------------------------------------------------------
# MockVisionProvider
# ---------------------------------------------------------------------------

def test_mock_provider_returns_canned_result_regardless_of_input():
    canned = VisionRecognitionResult(outcome=DetectionOutcome.RAW_FOOD, food_name="banana")
    provider = MockVisionProvider(canned)
    assert provider.recognize_food(b"anything") is canned
    assert provider.recognize_food(b"") is canned


# ---------------------------------------------------------------------------
# OpenAIVisionProvider — every outcome parses correctly
# ---------------------------------------------------------------------------

def test_raw_food_outcome_parses_correctly():
    client = _client_returning({
        "outcome": "raw_food",
        "food_name": "banana",
        "confidence": "high",
        "suggested_portion_label": "1 medium banana",
        "suggested_portion_grams": 118,
        "candidate_food_names": [],
        "detected_food_names": [],
    })
    provider = OpenAIVisionProvider(api_key="fake", model="fake-model", client=client)
    result = provider.recognize_food(b"fake image bytes")
    assert result.outcome == DetectionOutcome.RAW_FOOD
    assert result.food_name == "banana"
    assert result.confidence == "high"
    assert result.suggested_portion_grams == 118


def test_low_confidence_outcome_parses_correctly():
    client = _client_returning({
        "outcome": "low_confidence",
        "food_name": None,
        "confidence": None,
        "suggested_portion_label": None,
        "suggested_portion_grams": None,
        "candidate_food_names": ["sweet potato", "yam"],
        "detected_food_names": [],
    })
    provider = OpenAIVisionProvider(api_key="fake", model="fake-model", client=client)
    result = provider.recognize_food(b"fake image bytes")
    assert result.outcome == DetectionOutcome.LOW_CONFIDENCE
    assert result.candidate_food_names == ("sweet potato", "yam")


def test_multiple_foods_outcome_parses_correctly():
    client = _client_returning({
        "outcome": "multiple_foods",
        "food_name": None,
        "confidence": None,
        "suggested_portion_label": None,
        "suggested_portion_grams": None,
        "candidate_food_names": [],
        "detected_food_names": ["rice", "chicken curry"],
    })
    provider = OpenAIVisionProvider(api_key="fake", model="fake-model", client=client)
    result = provider.recognize_food(b"fake image bytes")
    assert result.outcome == DetectionOutcome.MULTIPLE_FOODS
    assert result.detected_food_names == ("rice", "chicken curry")


@pytest.mark.parametrize("outcome", ["package", "no_food_detected"])
def test_simple_outcomes_parse_correctly(outcome):
    client = _client_returning({
        "outcome": outcome,
        "food_name": None,
        "confidence": None,
        "suggested_portion_label": None,
        "suggested_portion_grams": None,
        "candidate_food_names": [],
        "detected_food_names": [],
    })
    provider = OpenAIVisionProvider(api_key="fake", model="fake-model", client=client)
    result = provider.recognize_food(b"fake image bytes")
    assert result.outcome == DetectionOutcome(outcome)


# ---------------------------------------------------------------------------
# Request shape — confirms what actually gets sent to the SDK
# ---------------------------------------------------------------------------

def test_request_includes_image_as_base64_data_uri():
    client = _client_returning({
        "outcome": "no_food_detected", "food_name": None, "confidence": None,
        "suggested_portion_label": None, "suggested_portion_grams": None,
        "candidate_food_names": [], "detected_food_names": [],
    })
    provider = OpenAIVisionProvider(api_key="fake", model="fake-model", client=client)
    provider.recognize_food(b"\x00\x01\x02", mime_type="image/png")

    sent = client.completions.last_call_kwargs
    assert sent["model"] == "fake-model"
    image_part = sent["messages"][1]["content"][1]
    assert image_part["type"] == "image_url"
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")


def test_request_uses_strict_json_schema_response_format():
    client = _client_returning({
        "outcome": "no_food_detected", "food_name": None, "confidence": None,
        "suggested_portion_label": None, "suggested_portion_grams": None,
        "candidate_food_names": [], "detected_food_names": [],
    })
    provider = OpenAIVisionProvider(api_key="fake", model="fake-model", client=client)
    provider.recognize_food(b"data")

    sent = client.completions.last_call_kwargs
    assert sent["response_format"]["type"] == "json_schema"
    assert sent["response_format"]["json_schema"]["strict"] is True


# ---------------------------------------------------------------------------
# JSON schema structural sanity — guards against a future edit accidentally
# breaking OpenAI strict-mode compliance (every property required,
# additionalProperties false)
# ---------------------------------------------------------------------------

def test_json_schema_is_strict_mode_compliant():
    schema = _JSON_SCHEMA["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"].keys())


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

def test_api_exception_is_wrapped_in_vision_provider_error():
    client = _FakeOpenAIClient(exception=RuntimeError("connection reset"))
    provider = OpenAIVisionProvider(api_key="fake", model="fake-model", client=client)
    with pytest.raises(VisionProviderError):
        provider.recognize_food(b"data")


def test_malformed_json_raises_vision_provider_error():
    client = _FakeOpenAIClient(content="this is not json")
    provider = OpenAIVisionProvider(api_key="fake", model="fake-model", client=client)
    with pytest.raises(VisionProviderError):
        provider.recognize_food(b"data")


def test_json_missing_required_field_raises_vision_provider_error():
    # Missing every field except outcome — should fail validation, not
    # silently proceed with None-filled garbage.
    client = _client_returning({"outcome": "raw_food"})
    provider = OpenAIVisionProvider(api_key="fake", model="fake-model", client=client)
    with pytest.raises(VisionProviderError):
        provider.recognize_food(b"data")


def test_json_with_invalid_outcome_value_raises_vision_provider_error():
    client = _client_returning({
        "outcome": "definitely_a_banana",  # not a real enum value
        "food_name": None, "confidence": None, "suggested_portion_label": None,
        "suggested_portion_grams": None, "candidate_food_names": [], "detected_food_names": [],
    })
    provider = OpenAIVisionProvider(api_key="fake", model="fake-model", client=client)
    with pytest.raises(VisionProviderError):
        provider.recognize_food(b"data")


def test_none_content_raises_vision_provider_error():
    client = _FakeOpenAIClient(content=None)
    provider = OpenAIVisionProvider(api_key="fake", model="fake-model", client=client)
    with pytest.raises(VisionProviderError):
        provider.recognize_food(b"data")


def test_empty_model_name_rejected_at_construction():
    with pytest.raises(ValueError):
        OpenAIVisionProvider(api_key="fake", model="", client=_FakeOpenAIClient())
