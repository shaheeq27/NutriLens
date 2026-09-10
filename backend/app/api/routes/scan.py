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

from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.providers.google_vision import OcrProvider
from app.contracts.scan_contract import ScanResponse
from app.providers.openai_vision import VisionProvider
from app.services.scan_orchestrator import (
    handle_initial_scan,
    handle_label_submission,
    handle_raw_food_confirmation,
)
from app.providers.usda_fooddata import NutritionLookupProvider

router = APIRouter()


def get_vision_provider() -> VisionProvider:
    raise NotImplementedError(
        "Vision provider not wired to real config yet — see main.py's docstring."
    )


def get_ocr_provider() -> OcrProvider:
    raise NotImplementedError(
        "OCR provider not wired to real config yet — see main.py's docstring."
    )


def get_nutrition_provider() -> NutritionLookupProvider:
    raise NotImplementedError(
        "Nutrition provider not wired to real config yet — see main.py's docstring."
    )


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