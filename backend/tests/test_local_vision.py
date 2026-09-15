import pytest
from app.providers.local_vision import MockVisionProvider, VisionRecognitionResult, DetectionOutcome, LocalVisionProvider

def test_mock_provider_returns_canned_result_regardless_of_input():
    canned = VisionRecognitionResult(outcome=DetectionOutcome.RAW_FOOD, food_name="banana")
    provider = MockVisionProvider(canned)
    assert provider.recognize_food(b"anything") is canned

class MockClassifier:
    def __init__(self, results):
        self._results = results
    def __call__(self, image, candidate_labels):
        return self._results

def _mocked_provider(results):
    # Don't download model, just mock classifier
    class DummyProvider(LocalVisionProvider):
        def __init__(self):
            self._candidate_labels = ["a non-food item", "multiple different foods", "a packaged food product", "an apple"]
            self._classifier = MockClassifier(results)
    return DummyProvider()

def test_local_vision_low_confidence_rejection():
    # score below 0.3 should be low confidence
    results = [
        {"label": "an apple", "score": 0.10},
        {"label": "a non-food item", "score": 0.10},
    ]
    provider = _mocked_provider(results)
    # mock Image.open
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "JPEG")

    res = provider.recognize_food(buf.getvalue())
    assert res.outcome == DetectionOutcome.LOW_CONFIDENCE
    assert res.candidate_food_names == ("an apple", "a non-food item")

def test_local_vision_multiple_foods():
    results = [
        {"label": "multiple different foods", "score": 0.95},
        {"label": "an apple", "score": 0.02},
    ]
    provider = _mocked_provider(results)
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "JPEG")

    res = provider.recognize_food(buf.getvalue())
    assert res.outcome == DetectionOutcome.MULTIPLE_FOODS

def test_local_vision_non_food():
    results = [
        {"label": "a non-food item", "score": 0.88},
    ]
    provider = _mocked_provider(results)
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "JPEG")

    res = provider.recognize_food(buf.getvalue())
    assert res.outcome == DetectionOutcome.NO_FOOD_DETECTED

def test_local_vision_raw_food():
    results = [
        {"label": "an apple", "score": 0.90},
    ]
    provider = _mocked_provider(results)
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "JPEG")

    res = provider.recognize_food(buf.getvalue())
    assert res.outcome == DetectionOutcome.RAW_FOOD
    assert res.food_name == "Apple"
    assert res.suggested_portion_grams is None
    assert res.suggested_portion_label is None

def test_local_vision_ambiguous_candidates_rejection():
    # top = 0.41, second = 0.40 -> gap = 0.01 < 0.05 margin -> LOW_CONFIDENCE
    results = [
        {"label": "a peach", "score": 0.41},
        {"label": "a mango", "score": 0.40},
    ]
    provider = _mocked_provider(results)
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "JPEG")

    res = provider.recognize_food(buf.getvalue())
    assert res.outcome == DetectionOutcome.LOW_CONFIDENCE

def test_local_vision_unsupported_food():
    results = [
        {"label": "an unknown or unsupported food item", "score": 0.88},
    ]
    from app.providers.local_vision import LocalVisionProvider
    class DummyProvider(LocalVisionProvider):
        def __init__(self):
            self._candidate_labels = ["an unknown or unsupported food item"]
            self._classifier = MockClassifier(results)
    provider = DummyProvider()
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "JPEG")

    res = provider.recognize_food(buf.getvalue())
    assert res.outcome == DetectionOutcome.LOW_CONFIDENCE
