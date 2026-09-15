from __future__ import annotations

import io
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol, runtime_checkable

from PIL import Image

class VisionProviderError(Exception):
    pass

class DetectionOutcome(str, Enum):
    RAW_FOOD = "raw_food"
    PACKAGE = "package"
    NO_FOOD_DETECTED = "no_food_detected"
    LOW_CONFIDENCE = "low_confidence"
    MULTIPLE_FOODS = "multiple_foods"

@dataclass(frozen=True)
class VisionRecognitionResult:
    outcome: DetectionOutcome
    food_name: Optional[str] = None
    confidence: Optional[str] = None  # "high" | "medium" | "low"
    suggested_portion_label: Optional[str] = None
    suggested_portion_grams: Optional[float] = None
    candidate_food_names: tuple[str, ...] = ()
    detected_food_names: tuple[str, ...] = ()

@runtime_checkable
class VisionProvider(Protocol):
    def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionRecognitionResult: ...

class MockVisionProvider:
    def __init__(self, canned_result: VisionRecognitionResult):
        self._canned_result = canned_result

    def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionRecognitionResult:
        return self._canned_result


MIN_CONFIDENCE = 0.25
MIN_CONFIDENCE_MARGIN = 0.05

class LocalVisionProvider:

    """Real local implementation using Hugging Face transformers (zero-shot CLIP)."""

    def __init__(self, model_id: str = "openai/clip-vit-base-patch32"):
        from transformers import pipeline
        self._classifier = pipeline("zero-shot-image-classification", model=model_id)

        # We define a curated list of target classes to identify raw foods vs packages.
        self._candidate_labels = [
            "a packaged food product",
            "a nutrition label",
            "a non-food item",
            "multiple different foods",
            "an unknown or unsupported food item",
            "an apple", "a banana", "an orange", "a strawberry", "a blueberry", "a raspberry", "a blackberry", "a grape", "a watermelon", "a cantaloupe", "a peach", "a pear", "a plum", "a cherry", "a lemon", "a lime", "a grapefruit", "a pineapple", "a mango", "a papaya", "a kiwi",
            "a broccoli", "a carrot", "a tomato", "a potato", "an onion", "a garlic", "a spinach", "a lettuce", "a cucumber", "a bell pepper", "a celery", "a mushroom", "a zucchini", "a squash", "a cauliflower", "a cabbage", "a Brussels sprout", "a green bean", "a pea", "a corn",
            "a salad", "a pizza", "a sandwich", "a burger", "a hot dog", "a taco", "a burrito", "a bowl of cereal", "a bowl of soup", "a pasta dish", "a sushi roll",
            "a piece of bread", "a piece of cake", "a cookie", "a brownie", "a donut", "a muffin", "a croissant", "a pancake", "a waffle",
            "a chicken breast", "a steak", "a pork chop", "a piece of fish", "a shrimp", "a bacon", "a sausage", "a hot dog",
            "an egg", "a cheese", "a yogurt", "a milk", "a butter",
            "a nut", "a peanut", "a almond", "a walnut", "a pecan", "a pistachio", "a cashew"
        ]

    def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionRecognitionResult:
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            results = self._classifier(image, candidate_labels=self._candidate_labels)
        except Exception as exc:
            raise VisionProviderError(f"Local vision model failed: {exc}") from exc

        if not results:
            return VisionRecognitionResult(outcome=DetectionOutcome.NO_FOOD_DETECTED)

        top_match = results[0]
        top_label = top_match["label"]
        top_score = top_match["score"]

        second_score = results[1]["score"] if len(results) > 1 else 0.0

        # If highest confidence is still very low, or it's ambiguous between top two choices, reject
        if top_score < MIN_CONFIDENCE or (top_score - second_score) < MIN_CONFIDENCE_MARGIN:
            return VisionRecognitionResult(
                outcome=DetectionOutcome.LOW_CONFIDENCE,
                candidate_food_names=tuple([r["label"] for r in results[:3]])
            )

        if top_label == "a non-food item":
            return VisionRecognitionResult(outcome=DetectionOutcome.NO_FOOD_DETECTED)

        if top_label == "multiple different foods":
            return VisionRecognitionResult(outcome=DetectionOutcome.MULTIPLE_FOODS)

        if top_label == "an unknown or unsupported food item":
            return VisionRecognitionResult(
                outcome=DetectionOutcome.LOW_CONFIDENCE,
                candidate_food_names=tuple([r["label"] for r in results[1:4]])
            )

        if top_label in ["a packaged food product", "a nutrition label"]:
            return VisionRecognitionResult(
                outcome=DetectionOutcome.PACKAGE,
                food_name="Packaged Product",
            )

        # It's a raw food
        food_name = top_label.replace("a ", "").replace("an ", "").title()

        confidence_str = "high"
        if top_score < 0.6:
            confidence_str = "medium"

        return VisionRecognitionResult(
            outcome=DetectionOutcome.RAW_FOOD,
            food_name=food_name,
            confidence=confidence_str,
            suggested_portion_label=None,
            suggested_portion_grams=None,
            candidate_food_names=tuple([r["label"].replace("a ", "").replace("an ", "").title() for r in results[1:4]])
        )
