"""
NutriLens backend — food recognition service.

Composes image_validation, photo_privacy, and a VisionProvider into the
raw-food/package recognition step of the scan flow: validate the upload,
strip its EXIF metadata, then ask the vision provider what it sees.

This is the seam between "an uploaded photo" and "a food/package
identification." It does not touch nutrition values at all (that's
nutrition_lookup.py's and label_ocr.py's job), and it does not know
about the final response contract (still unresolved as of this writing)
— same reasoning as every other Lane B file so far.

Never raises for expected failure modes (bad image, provider error) —
those come back as a FoodRecognitionResult so a caller (eventually
scan_orchestrator.py) can handle every case uniformly with one type,
rather than mixing exceptions and return values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.services.image_validation import ImageValidationError, validate_image_upload, ImageRejectionReason
from app.providers.openai_vision import DetectionOutcome, VisionProvider, VisionProviderError
from app.services.photo_privacy import strip_exif


class FoodRecognitionOutcome(str, Enum):
    """Mirrors openai_vision.DetectionOutcome plus the upstream failure
    modes this service adds on top of it (image validation, provider
    failure)."""

    RAW_FOOD = "raw_food"
    PACKAGE = "package"
    NO_FOOD_DETECTED = "no_food_detected"
    LOW_CONFIDENCE = "low_confidence"
    MULTIPLE_FOODS = "multiple_foods"
    INVALID_IMAGE = "invalid_image"
    PROVIDER_ERROR = "provider_error"


@dataclass(frozen=True)
class FoodRecognitionResult:
    outcome: FoodRecognitionOutcome
    food_name: Optional[str] = None
    confidence: Optional[str] = None
    suggested_portion_label: Optional[str] = None
    suggested_portion_grams: Optional[float] = None
    candidate_food_names: tuple[str, ...] = ()
    detected_food_names: tuple[str, ...] = ()
    message: Optional[str] = None
    image_rejection_reason: Optional[ImageRejectionReason] = None  # populated for invalid_image / provider_error


_OUTCOME_MAP: dict[DetectionOutcome, FoodRecognitionOutcome] = {
    DetectionOutcome.RAW_FOOD: FoodRecognitionOutcome.RAW_FOOD,
    DetectionOutcome.PACKAGE: FoodRecognitionOutcome.PACKAGE,
    DetectionOutcome.NO_FOOD_DETECTED: FoodRecognitionOutcome.NO_FOOD_DETECTED,
    DetectionOutcome.LOW_CONFIDENCE: FoodRecognitionOutcome.LOW_CONFIDENCE,
    DetectionOutcome.MULTIPLE_FOODS: FoodRecognitionOutcome.MULTIPLE_FOODS,
}


def recognize_food_photo(image_bytes: bytes, vision_provider: VisionProvider) -> FoodRecognitionResult:
    """The actual composed step: validate -> strip EXIF -> recognize."""
    validation_result = validate_image_upload(image_bytes)
    if isinstance(validation_result, ImageValidationError):
        return FoodRecognitionResult(
            outcome=FoodRecognitionOutcome.INVALID_IMAGE,
            message=validation_result.message, image_rejection_reason=validation_result.reason,
        )

    cleaned_bytes = strip_exif(validation_result.data)

    try:
        vision_result = vision_provider.recognize_food(cleaned_bytes, mime_type=validation_result.format)
    except VisionProviderError as exc:
        return FoodRecognitionResult(
            outcome=FoodRecognitionOutcome.PROVIDER_ERROR,
            message=str(exc),
        )

    return FoodRecognitionResult(
        outcome=_OUTCOME_MAP[vision_result.outcome],
        food_name=vision_result.food_name,
        confidence=vision_result.confidence,
        suggested_portion_label=vision_result.suggested_portion_label,
        suggested_portion_grams=vision_result.suggested_portion_grams,
        candidate_food_names=vision_result.candidate_food_names,
        detected_food_names=vision_result.detected_food_names,
    )