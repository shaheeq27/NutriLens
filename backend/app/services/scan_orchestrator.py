"""
NutriLens backend — scan orchestrator.

Composes food_recognition, label_ocr, and nutrition_lookup into the full
scan flow. Stateless by design (V1 has no accounts/sessions): each
function here is one HTTP request's worth of work; the client carries
forward whatever it needs into the next request (e.g. the detected food
name, to send back alongside a confirmed quantity for
handle_raw_food_confirmation).
"""

from __future__ import annotations

from typing import Optional

from app.contracts.scan_contract import ScanResponse
from app.services.food_recognition import FoodRecognitionOutcome, FoodRecognitionResult, recognize_food_photo
from app.services.image_validation import ImageRejectionReason
from app.services.label_ocr import LabelExtractionOutcome, LabelExtractionResult, extract_label_nutrients
from app.services.nutrition_lookup import NutritionLookupOutcome, ScaledNutritionResult, lookup_and_scale_nutrition
from app.providers.openai_vision import VisionProvider
from app.providers.google_vision import OcrProvider
from app.providers.usda_fooddata import NutritionLookupProvider


def handle_initial_scan(image_bytes: bytes, vision_provider: VisionProvider) -> ScanResponse:
    """First step of any scan: identify what's in the photo."""
    result = recognize_food_photo(image_bytes, vision_provider)
    return _food_recognition_to_response(result)


def handle_raw_food_confirmation(
    food_name: str, portion_grams: float, nutrition_provider: NutritionLookupProvider
) -> ScanResponse:
    """Second step, raw-food path: client already has food_name from
    handle_initial_scan's response and confirms/edits the portion."""
    result = lookup_and_scale_nutrition(food_name, portion_grams, nutrition_provider)
    return _nutrition_lookup_to_response(result, original_food_name=food_name)


def handle_label_submission(image_bytes: bytes, ocr_provider: OcrProvider) -> ScanResponse:
    """Second step, packaged-food path: client submits the back/side
    label photo requested by handle_initial_scan's package_detected
    response."""
    result = extract_label_nutrients(image_bytes, ocr_provider)
    return _label_extraction_to_response(result)


# ---------------------------------------------------------------------------
# Mapping to the response shape — isolated here on purpose
# ---------------------------------------------------------------------------

def _map_image_rejection(reason: Optional[ImageRejectionReason], message: str) -> ScanResponse:
    """Maps internal image validation reasons to public contract.
    Safely falls back to an error state if reason is omitted or has no exact match."""
    if reason == ImageRejectionReason.FILE_TOO_LARGE:
        return {"status": "image_rejected", "reason": "file_too_large"}
    if reason == ImageRejectionReason.UNSUPPORTED_FORMAT:
        return {"status": "image_rejected", "reason": "unsupported_file_type"}
    if reason == ImageRejectionReason.DIMENSIONS_OUT_OF_RANGE:
        return {"status": "image_rejected", "reason": "dimensions_out_of_range"}

    # Contract is frozen and lacks empty/corrupt/decode exact matches.
    if reason == ImageRejectionReason.EMPTY_OR_CORRUPTED:
        return {"status": "error", "message": "No image data received or data is corrupted.", "retryable": True}
    if reason == ImageRejectionReason.DECODE_FAILED:
        return {"status": "error", "message": "This image could not be decoded. Please try a different photo.", "retryable": True}

    return {"status": "error", "message": message, "retryable": True}


def _food_recognition_to_response(result: FoodRecognitionResult) -> ScanResponse:
    if result.outcome == FoodRecognitionOutcome.RAW_FOOD:
        # Enforce contract guarantees
        if not result.food_name:
            return {"status": "error", "message": "Food name missing from recognition result.", "retryable": True}
        if result.suggested_portion_grams is None:
            return {"status": "error", "message": "Suggested portion size missing from recognition result.", "retryable": True}

        return {
            "status": "raw_food_detected",
            "food_name": result.food_name,
            # We omit "candidates" entirely because the service doesn't provide confidences,
            # and the contract allows omission via default_factory=list. We do NOT fabricate [].
            "suggested_quantity": {
                "amount": result.suggested_portion_grams,
                "unit": "g"
            }
        }

    if result.outcome == FoodRecognitionOutcome.PACKAGE:
        return {"status": "package_detected", "product_guess": None}

    if result.outcome == FoodRecognitionOutcome.NO_FOOD_DETECTED:
        return {"status": "no_food_detected"}

    if result.outcome == FoodRecognitionOutcome.LOW_CONFIDENCE:
        return {
            "status": "error",
            "message": "Could not identify the food with enough confidence. Please try another photo.",
            "retryable": True
        }

    if result.outcome == FoodRecognitionOutcome.MULTIPLE_FOODS:
        return {
            "status": "error",
            "message": "Multiple foods detected. Please scan one item at a time.",
            "retryable": True
        }

    if result.outcome == FoodRecognitionOutcome.INVALID_IMAGE:
        return _map_image_rejection(result.image_rejection_reason, result.message or "Invalid image")

    # PROVIDER_ERROR
    return {"status": "error", "message": result.message or "Provider error", "retryable": True}


def _nutrition_lookup_to_response(result: ScaledNutritionResult, original_food_name: str) -> ScanResponse:
    if result.outcome == NutritionLookupOutcome.FOUND:
        n = result.nutrients
        if n is None:
            return {"status": "error", "message": "Nutrition data missing.", "retryable": True}

        # Core fields are strictly required by the contract
        if n.energy_kcal is None or n.protein_g is None or n.carbohydrates_g is None or n.fat_g is None:
            return {"status": "error", "message": "Core nutrition data missing from provider.", "retryable": True}

        if result.fdc_id is None:
            return {"status": "error", "message": "FDC ID missing from provider.", "retryable": True}

        name_to_use = result.food_name or original_food_name
        if not name_to_use:
            return {"status": "error", "message": "Food name missing from provider.", "retryable": True}

        if result.portion_grams is None:
            return {"status": "error", "message": "Portion size missing from provider.", "retryable": True}

        return {
            "status": "nutrition_result",
            "source": {
                "source": "usda",
                "fdc_id": str(result.fdc_id),
                "usda_description": name_to_use,
            },
            "food_name": name_to_use,
            "quantity": {
                "amount": result.portion_grams,
                "unit": "g"
            },
            "nutrients": {
                "calories_kcal": n.energy_kcal,
                "protein_g": n.protein_g,
                "carbohydrates_g": n.carbohydrates_g,
                "fat_g": n.fat_g,
                "fiber_g": n.fiber_g,     # Preserves None if omitted by service
                "sugar_g": n.sugar_g,     # Preserves None if omitted by service
                "sodium_mg": n.sodium_mg, # Preserves None if omitted by service
                # potassium_mg and caffeine_mg are deliberately omitted per the frozen contract
            },
        }

    if result.outcome == NutritionLookupOutcome.NOT_FOUND:
        name_to_use = result.food_name or original_food_name
        if not name_to_use:
            return {"status": "error", "message": "Food name missing for not-found response.", "retryable": True}
        return {"status": "nutrition_not_found", "food_name": name_to_use}

    # PROVIDER_ERROR
    return {"status": "error", "message": result.message or "Provider error", "retryable": True}


def _label_extraction_to_response(result: LabelExtractionResult) -> ScanResponse:
    if result.outcome == LabelExtractionOutcome.EXTRACTED:
        return {
            "status": "label_ocr_extracted",
            "raw_fields": {str(k): str(v) for k, v in (result.extracted or {}).items()},
        }

    if result.outcome == LabelExtractionOutcome.INVALID_IMAGE:
        return _map_image_rejection(result.image_rejection_reason, result.message or "Invalid image")

    if result.outcome == LabelExtractionOutcome.NO_TEXT_DETECTED:
        return {
            "status": "ocr_validation_failed",
            "reason": "unreadable",
            "missing_fields": list(result.missing_fields),
        }

    if result.outcome == LabelExtractionOutcome.NOT_A_NUTRITION_LABEL:
        return {
            "status": "error",
            "message": "The image does not appear to contain a nutrition label. Please photograph the nutrition facts panel.",
            "retryable": True
        }

    # PROVIDER_ERROR
    return {"status": "error", "message": result.message or "Provider error", "retryable": True}