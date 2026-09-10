"""
NutriLens backend — scan orchestrator.

PROVISIONAL: the response shapes returned here are built against the
"frozen draft" 9-state table proposed in the project brief's §9, NOT
against a verified real backend/app/contracts/scan_contract.py — that
file's existence could not be confirmed in the repo as of this writing
(repo was still at 1 commit on last check, and no scan_contract.py
could be located). Treat every dict shape below as a placeholder.

The mapping from service-level outcomes (food_recognition.py,
label_ocr.py, nutrition_lookup.py — all of which are final, tested, and
NOT provisional) to this placeholder shape lives entirely in the three
small `_..._to_response` functions below. Reconciling against the real
contract later means editing those three functions, not the services
themselves, and not this file's public entry points.

Composes food_recognition, label_ocr, and nutrition_lookup into the full
scan flow. Stateless by design (V1 has no accounts/sessions): each
function here is one HTTP request's worth of work; the client carries
forward whatever it needs into the next request (e.g. the detected food
name, to send back alongside a confirmed quantity for
handle_raw_food_confirmation).
"""

from __future__ import annotations

from typing import Any

from app.services.food_recognition import FoodRecognitionOutcome, FoodRecognitionResult, recognize_food_photo
from app.services.label_ocr import LabelExtractionOutcome, LabelExtractionResult, extract_label_nutrients
from app.services.nutrition_lookup import NutritionLookupOutcome, ScaledNutritionResult, lookup_and_scale_nutrition
from app.providers.openai_vision import VisionProvider
from app.providers.google_vision import OcrProvider
from app.providers.usda_fooddata import NutritionLookupProvider


def handle_initial_scan(image_bytes: bytes, vision_provider: VisionProvider) -> dict[str, Any]:
    """First step of any scan: identify what's in the photo."""
    result = recognize_food_photo(image_bytes, vision_provider)
    return _food_recognition_to_response(result)


def handle_raw_food_confirmation(
    food_name: str, portion_grams: float, nutrition_provider: NutritionLookupProvider
) -> dict[str, Any]:
    """Second step, raw-food path: client already has food_name from
    handle_initial_scan's response and confirms/edits the portion."""
    result = lookup_and_scale_nutrition(food_name, portion_grams, nutrition_provider)
    return _nutrition_lookup_to_response(result)


def handle_label_submission(image_bytes: bytes, ocr_provider: OcrProvider) -> dict[str, Any]:
    """Second step, packaged-food path: client submits the back/side
    label photo requested by handle_initial_scan's package_detected
    response."""
    result = extract_label_nutrients(image_bytes, ocr_provider)
    return _label_extraction_to_response(result)


# ---------------------------------------------------------------------------
# Mapping to the provisional response shape — isolated here on purpose
# ---------------------------------------------------------------------------

def _food_recognition_to_response(result: FoodRecognitionResult) -> dict[str, Any]:
    if result.outcome == FoodRecognitionOutcome.RAW_FOOD:
        return {
            "status": "raw_food_detected",
            "food_name": result.food_name,
            "confidence": result.confidence,
            "suggested_portion_label": result.suggested_portion_label,
            "suggested_portion_grams": result.suggested_portion_grams,
        }
    if result.outcome == FoodRecognitionOutcome.PACKAGE:
        return {"status": "package_detected"}
    if result.outcome == FoodRecognitionOutcome.NO_FOOD_DETECTED:
        return {"status": "no_food_detected"}
    if result.outcome == FoodRecognitionOutcome.LOW_CONFIDENCE:
        return {"status": "low_confidence", "candidate_food_names": list(result.candidate_food_names)}
    if result.outcome == FoodRecognitionOutcome.MULTIPLE_FOODS:
        return {"status": "multiple_foods", "detected_food_names": list(result.detected_food_names)}
    if result.outcome == FoodRecognitionOutcome.INVALID_IMAGE:
        return {"status": "image_rejected", "reason": result.message}
    # PROVIDER_ERROR
    return {"status": "error", "message": result.message, "retryable": True}


def _nutrition_lookup_to_response(result: ScaledNutritionResult) -> dict[str, Any]:
    if result.outcome == NutritionLookupOutcome.FOUND:
        n = result.nutrients
        return {
            "status": "nutrition_result",
            "source": "usda",
            "food_name": result.food_name,
            "quantity_grams": result.portion_grams,
            "nutrients": {
                "energy_kcal": n.energy_kcal,
                "protein_g": n.protein_g,
                "carbohydrates_g": n.carbohydrates_g,
                "fat_g": n.fat_g,
                "fiber_g": n.fiber_g,
                "sugar_g": n.sugar_g,
                "sodium_mg": n.sodium_mg,
                "potassium_mg": n.potassium_mg,
                "caffeine_mg": n.caffeine_mg,
            },
        }
    if result.outcome == NutritionLookupOutcome.NOT_FOUND:
        return {"status": "nutrition_not_found", "food_name": result.food_name or ""}
    # PROVIDER_ERROR
    return {"status": "error", "message": result.message, "retryable": True}


def _label_extraction_to_response(result: LabelExtractionResult) -> dict[str, Any]:
    if result.outcome == LabelExtractionOutcome.EXTRACTED:
        return {
            "status": "label_ocr_extracted",
            "serving_basis": result.serving_basis,
            "raw_fields": result.extracted,
            "missing_fields": list(result.missing_fields),
        }
    if result.outcome == LabelExtractionOutcome.INVALID_IMAGE:
        return {"status": "image_rejected", "reason": result.message}
    if result.outcome in (LabelExtractionOutcome.NO_TEXT_DETECTED, LabelExtractionOutcome.NOT_A_NUTRITION_LABEL):
        return {
            "status": "ocr_validation_failed",
            "reason": result.outcome.value,
            "message": result.message,
        }
    # PROVIDER_ERROR
    return {"status": "error", "message": result.message, "retryable": True}