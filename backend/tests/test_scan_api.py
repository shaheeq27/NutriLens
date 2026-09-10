"""
Tests for backend/app/api/routes/scan.py + main.py, end to end.
Run with: pytest test_scan_api.py -v

Uses a real FastAPI TestClient against the real app — only the provider
dependencies are swapped via app.dependency_overrides, so this exercises
the actual routing, request parsing, and orchestrator wiring, not a
reimplementation of it.
"""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.providers.google_vision import MockOcrProvider, OcrRejection, OcrRejectionReason, OcrResult
from app.main import app
from app.providers.openai_vision import DetectionOutcome, MockVisionProvider, VisionRecognitionResult
from app.api.routes.scan import get_nutrition_provider, get_ocr_provider, get_vision_provider
from app.providers.usda_fooddata import (
    MockNutritionLookupProvider,
    UsdaFoodMatch,
    UsdaLookupReason,
    UsdaLookupRejection,
    UsdaNutrients,
)


@pytest.fixture(autouse=True)
def _clear_overrides():
    """Every test sets its own overrides; make sure none leak between tests."""
    yield
    app.dependency_overrides.clear()


def _client() -> TestClient:
    return TestClient(app)


def _valid_jpeg_bytes(width=300, height=300) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(10, 20, 30)).save(buf, format="JPEG")
    return buf.getvalue()


def _too_small_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (50, 50)).save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health_endpoint():
    response = _client().get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /scan
# ---------------------------------------------------------------------------

def test_scan_raw_food_detected():
    canned = VisionRecognitionResult(
        outcome=DetectionOutcome.RAW_FOOD,
        food_name="banana",
        confidence="high",
        suggested_portion_label="1 medium banana",
        suggested_portion_grams=118.0,
    )
    app.dependency_overrides[get_vision_provider] = lambda: MockVisionProvider(canned)

    response = _client().post("/scan", files={"file": ("test.jpg", _valid_jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "raw_food_detected"
    assert body["food_name"] == "banana"
    assert body["suggested_portion_grams"] == 118.0


def test_scan_package_detected():
    canned = VisionRecognitionResult(outcome=DetectionOutcome.PACKAGE)
    app.dependency_overrides[get_vision_provider] = lambda: MockVisionProvider(canned)

    response = _client().post("/scan", files={"file": ("test.jpg", _valid_jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 200
    assert response.json() == {"status": "package_detected"}


def test_scan_invalid_image_rejected_before_reaching_provider():
    app.dependency_overrides[get_vision_provider] = lambda: MockVisionProvider(
        VisionRecognitionResult(outcome=DetectionOutcome.RAW_FOOD)  # would be wrong if ever reached
    )

    response = _client().post("/scan", files={"file": ("tiny.jpg", _too_small_jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 200
    assert response.json()["status"] == "image_rejected"


def test_scan_multiple_foods_detected():
    canned = VisionRecognitionResult(
        outcome=DetectionOutcome.MULTIPLE_FOODS,
        detected_food_names=("rice", "chicken curry"),
    )
    app.dependency_overrides[get_vision_provider] = lambda: MockVisionProvider(canned)

    response = _client().post("/scan", files={"file": ("test.jpg", _valid_jpeg_bytes(), "image/jpeg")})
    body = response.json()
    assert body["status"] == "multiple_foods"
    assert body["detected_food_names"] == ["rice", "chicken curry"]


# ---------------------------------------------------------------------------
# POST /scan/raw-food
# ---------------------------------------------------------------------------

def test_confirm_raw_food_returns_nutrition_result():
    match = UsdaFoodMatch(
        fdc_id=1105073,
        description="Bananas, raw",
        nutrients=UsdaNutrients(energy_kcal=89.0, protein_g=1.09, carbohydrates_g=22.8, fat_g=0.33),
    )
    app.dependency_overrides[get_nutrition_provider] = lambda: MockNutritionLookupProvider(match)

    response = _client().post("/scan/raw-food", data={"food_name": "banana", "portion_grams": 118})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "nutrition_result"
    assert body["source"] == "usda"
    assert body["nutrients"]["energy_kcal"] == 105.02


def test_confirm_raw_food_not_found():
    rejection = UsdaLookupRejection(reason=UsdaLookupReason.NO_MATCH, message="no match")
    app.dependency_overrides[get_nutrition_provider] = lambda: MockNutritionLookupProvider(rejection)

    response = _client().post("/scan/raw-food", data={"food_name": "dragon fruit", "portion_grams": 100})
    assert response.status_code == 200
    assert response.json()["status"] == "nutrition_not_found"


# ---------------------------------------------------------------------------
# POST /scan/label
# ---------------------------------------------------------------------------

def test_submit_label_extracted_successfully():
    label_text = "Calories 140\nTotal Fat 7g\nTotal Carbohydrate 18g\nProtein 2g\nServing Size 30g"
    app.dependency_overrides[get_ocr_provider] = lambda: MockOcrProvider(OcrResult(raw_text=label_text))

    response = _client().post("/scan/label", files={"file": ("label.jpg", _valid_jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "label_ocr_extracted"
    assert body["raw_fields"]["energy_kcal"] == 140


def test_submit_label_no_text_detected():
    rejection = OcrRejection(reason=OcrRejectionReason.NO_TEXT_DETECTED, message="no text found")
    app.dependency_overrides[get_ocr_provider] = lambda: MockOcrProvider(rejection)

    response = _client().post("/scan/label", files={"file": ("label.jpg", _valid_jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 200
    assert response.json()["status"] == "ocr_validation_failed"


def test_submit_label_invalid_image_rejected_before_ocr():
    app.dependency_overrides[get_ocr_provider] = lambda: MockOcrProvider(OcrResult(raw_text="Calories 100"))

    response = _client().post("/scan/label", files={"file": ("tiny.jpg", _too_small_jpeg_bytes(), "image/jpeg")})
    assert response.json()["status"] == "image_rejected"


# ---------------------------------------------------------------------------
# Unwired providers — honest failure, not a silent wrong answer
# ---------------------------------------------------------------------------

def test_scan_without_override_raises_not_implemented():
    """No dependency_overrides set — confirms the routes are honestly
    unwired rather than silently falling back to something real-looking."""
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/scan", files={"file": ("test.jpg", _valid_jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 500