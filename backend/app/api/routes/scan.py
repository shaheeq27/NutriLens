"""
NutriLens backend — scan API routes.

PROVISIONAL, same reasoning as scan_orchestrator.py: response shapes
come from the brief's draft §9 table, not a verified real contract.

Three endpoints, stateless (V1 has no accounts/sessions):
  POST /scan             - submit a photo, get back what it detected
  POST /scan/raw-food     - confirm food name + portion, get nutrition
  POST /scan/label        - submit a back/side label photo, get extracted values

Provider instances are injected via FastAPI dependencies (`get_*_provider`
below) so tests can swap in Mock providers via `app.dependency_overrides`
without touching this file at all — see test_scan_api.py. The real
implementations are intentionally left unwired (NotImplementedError)
rather than guessing at credentials from an env-var scheme that might
not match the real .env.example — see main.py's docstring for the same
flag.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.providers.google_vision import OcrProvider, MockOcrProvider, OcrResult, GoogleVisionOcrProvider
from app.contracts.scan_contract import ScanResponse, LabelValidationRequest
from app.providers.openai_vision import VisionProvider, MockVisionProvider, VisionRecognitionResult, DetectionOutcome, OpenAIVisionProvider
from app.services.scan_orchestrator import (
    handle_initial_scan,
    handle_label_submission,
    handle_raw_food_confirmation,
    handle_label_validation,
)
from app.providers.usda_fooddata import NutritionLookupProvider, MockNutritionLookupProvider, UsdaFoodMatch, UsdaNutrients, UsdaFoodDataProvider
from app.core.config import get_settings

router = APIRouter()


def get_vision_provider() -> VisionProvider:
    settings = get_settings()
    if settings.use_mock_providers:
        return MockVisionProvider(VisionRecognitionResult(
            outcome=DetectionOutcome.RAW_FOOD, food_name="banana", confidence="high",
            suggested_portion_label="1 medium banana", suggested_portion_grams=118.0,
        ))
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required when USE_MOCK_PROVIDERS=false")
    return OpenAIVisionProvider(settings.openai_api_key, settings.openai_vision_model)


def get_ocr_provider() -> OcrProvider:
    settings = get_settings()
    if settings.use_mock_providers:
        return MockOcrProvider(OcrResult(
            raw_text="Serving Size 30g\nCalories 140\nTotal Fat 7g\nTotal Carbohydrate 18g\nProtein 2g\nTotal Sugars 12g\nSodium 90mg"
        ))
    return GoogleVisionOcrProvider(settings.google_application_credentials)


def get_nutrition_provider() -> NutritionLookupProvider:
    settings = get_settings()
    if settings.use_mock_providers:
        return MockNutritionLookupProvider(UsdaFoodMatch(
            fdc_id=173944, description="Bananas, raw", nutrients=UsdaNutrients(
                energy_kcal=89, protein_g=1.09, carbohydrates_g=22.84, fat_g=0.33,
                fiber_g=2.6, sugar_g=12.23, sodium_mg=1,
            )
        ))
    if not settings.usda_fooddata_api_key:
        raise RuntimeError("USDA_FOODDATA_API_KEY is required when USE_MOCK_PROVIDERS=false")
    return UsdaFoodDataProvider(settings.usda_fooddata_api_key)


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
