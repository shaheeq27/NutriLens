"""
Tests for backend/app/services/food_recognition.py.
Run with: pytest test_food_recognition.py -v
"""

import io

import pytest
from PIL import Image

from app.services.food_recognition import FoodRecognitionOutcome, recognize_food_photo
from app.providers.openai_vision import DetectionOutcome, MockVisionProvider, VisionProviderError, VisionRecognitionResult


def _valid_jpeg(width=300, height=300) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(10, 20, 30)).save(buf, format="JPEG")
    return buf.getvalue()


class _FailingVisionProvider:
    """Test double that always raises — MockVisionProvider can't do this
    since it's designed to always succeed with a canned result."""

    def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg"):
        raise VisionProviderError("simulated provider outage")


# ---------------------------------------------------------------------------
# Happy paths — every DetectionOutcome maps through correctly
# ---------------------------------------------------------------------------

def test_raw_food_outcome_passes_through_with_all_fields():
    canned = VisionRecognitionResult(
        outcome=DetectionOutcome.RAW_FOOD,
        food_name="banana",
        confidence="high",
        suggested_portion_label="1 medium banana",
        suggested_portion_grams=118.0,
    )
    result = recognize_food_photo(_valid_jpeg(), MockVisionProvider(canned))
    assert result.outcome == FoodRecognitionOutcome.RAW_FOOD
    assert result.food_name == "banana"
    assert result.suggested_portion_grams == 118.0


def test_package_outcome_passes_through():
    canned = VisionRecognitionResult(outcome=DetectionOutcome.PACKAGE)
    result = recognize_food_photo(_valid_jpeg(), MockVisionProvider(canned))
    assert result.outcome == FoodRecognitionOutcome.PACKAGE


def test_no_food_detected_outcome_passes_through():
    canned = VisionRecognitionResult(outcome=DetectionOutcome.NO_FOOD_DETECTED)
    result = recognize_food_photo(_valid_jpeg(), MockVisionProvider(canned))
    assert result.outcome == FoodRecognitionOutcome.NO_FOOD_DETECTED


def test_low_confidence_outcome_carries_candidates():
    canned = VisionRecognitionResult(
        outcome=DetectionOutcome.LOW_CONFIDENCE,
        candidate_food_names=("sweet potato", "yam"),
    )
    result = recognize_food_photo(_valid_jpeg(), MockVisionProvider(canned))
    assert result.outcome == FoodRecognitionOutcome.LOW_CONFIDENCE
    assert result.candidate_food_names == ("sweet potato", "yam")


def test_multiple_foods_outcome_carries_detected_names():
    canned = VisionRecognitionResult(
        outcome=DetectionOutcome.MULTIPLE_FOODS,
        detected_food_names=("rice", "chicken curry"),
    )
    result = recognize_food_photo(_valid_jpeg(), MockVisionProvider(canned))
    assert result.outcome == FoodRecognitionOutcome.MULTIPLE_FOODS
    assert result.detected_food_names == ("rice", "chicken curry")


# ---------------------------------------------------------------------------
# Failure paths — invalid image and provider error
# ---------------------------------------------------------------------------

def test_invalid_image_short_circuits_before_calling_the_provider():
    """A too-small image should be rejected by image_validation and never
    even reach the vision provider — proven by using a provider that
    would raise if it were ever called."""
    too_small = io.BytesIO()
    Image.new("RGB", (50, 50)).save(too_small, format="JPEG")

    result = recognize_food_photo(too_small.getvalue(), _FailingVisionProvider())
    assert result.outcome == FoodRecognitionOutcome.INVALID_IMAGE
    assert result.message is not None


def test_provider_error_is_captured_not_raised():
    result = recognize_food_photo(_valid_jpeg(), _FailingVisionProvider())
    assert result.outcome == FoodRecognitionOutcome.PROVIDER_ERROR
    assert "simulated provider outage" in result.message


# ---------------------------------------------------------------------------
# EXIF stripping actually happens before the provider sees the image
# ---------------------------------------------------------------------------

def test_image_passed_to_provider_has_exif_stripped():
    im = Image.new("RGB", (300, 300), color=(5, 5, 5))
    exif = im.getexif()
    exif[271] = "SomeCameraMake"
    buf = io.BytesIO()
    im.save(buf, format="JPEG", exif=exif)
    original_with_exif = buf.getvalue()

    captured = {}

    class _CapturingProvider:
        def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg"):
            captured["bytes"] = image_bytes
            return VisionRecognitionResult(outcome=DetectionOutcome.NO_FOOD_DETECTED)

    recognize_food_photo(original_with_exif, _CapturingProvider())

    reopened = Image.open(io.BytesIO(captured["bytes"]))
    assert dict(reopened.getexif()) == {}
