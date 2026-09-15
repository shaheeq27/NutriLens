"""
NutriLens backend — scan API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.providers.local_ocr import OcrProvider, MockOcrProvider, OcrExtractionResult, EasyOcrProvider
from app.contracts.scan_contract import ScanResponse, LabelValidationRequest
from app.providers.local_vision import VisionProvider, MockVisionProvider, VisionRecognitionResult, DetectionOutcome, LocalVisionProvider
from app.services.scan_orchestrator import (
    handle_initial_scan,
    handle_label_submission,
    handle_raw_food_confirmation,
    handle_label_validation,
)
from app.providers.openfoodfacts import NutritionLookupProvider, MockNutritionLookupProvider, DatabaseFoodMatch, DatabaseNutrients, OpenFoodFactsProvider
from app.core.config import get_settings

router = APIRouter()


def get_vision_provider() -> VisionProvider:
    settings = get_settings()
    if settings.use_mock_providers:
        return MockVisionProvider(VisionRecognitionResult(
            outcome=DetectionOutcome.RAW_FOOD, food_name="banana", confidence="high",
            suggested_portion_label="1 medium banana", suggested_portion_grams=118.0,
        ))
    return LocalVisionProvider()


def get_ocr_provider() -> OcrProvider:
    settings = get_settings()
    if settings.use_mock_providers:
        return MockOcrProvider(OcrExtractionResult(
            raw_text_blocks=("Serving Size 30g", "Calories 140", "Total Fat 7g", "Total Carbohydrate 18g", "Protein 2g", "Total Sugars 12g", "Sodium 90mg"),
            provider_confidence=0.9
        ))
    return EasyOcrProvider()


def get_nutrition_provider() -> NutritionLookupProvider:
    settings = get_settings()
    if settings.use_mock_providers:
        return MockNutritionLookupProvider(DatabaseFoodMatch(
            db_id="173944", description="Bananas, raw", nutrients=DatabaseNutrients(
                energy_kcal=89.0, protein_g=1.09, carbohydrates_g=22.84, fat_g=0.33,
                fiber_g=2.6, sugar_g=12.23, sodium_mg=1.0,
            )
        ))
    return OpenFoodFactsProvider()


@router.post("/scan", response_model=ScanResponse)
async def submit_scan(
    file: UploadFile = File(...),
    vision_provider: VisionProvider = Depends(get_vision_provider),
) -> ScanResponse:
    image_bytes = await file.read()
    return handle_initial_scan(image_bytes, vision_provider)


@router.post("/scan/raw-food", response_model=ScanResponse)
async def confirm_raw_food(
    food_name: str = Form(...),
    portion_grams: float = Form(...),
    nutrition_provider: NutritionLookupProvider = Depends(get_nutrition_provider),
) -> ScanResponse:
    return handle_raw_food_confirmation(food_name, portion_grams, nutrition_provider)


@router.post("/scan/label", response_model=ScanResponse)
async def submit_label(
    file: UploadFile = File(...),
    ocr_provider: OcrProvider = Depends(get_ocr_provider),
) -> ScanResponse:
    image_bytes = await file.read()
    return handle_label_submission(image_bytes, ocr_provider)


@router.post("/scan/label/validate", response_model=ScanResponse)
async def validate_label(
    request: LabelValidationRequest,
) -> ScanResponse:
    return handle_label_validation(request)
