import pytest
from app.contracts.scan_contract import LabelValidationRequest

def test_label_validation_success():
    from app.services.scan_orchestrator import handle_label_validation
    req = LabelValidationRequest(
        raw_fields={"energy_kcal": "150", "protein_g": "5", "fat_g": "2", "carbohydrates_g": "20", "sugar_g": "15"},
        serving_basis="per 1 cup",
        product_guess="Cheerios"
    )
    result = handle_label_validation(req)
    assert result["status"] == "nutrition_result"
    assert result["food_name"] == "Cheerios"
    assert result["serving_basis"] == "per 1 cup"
    assert result["quantity"] is None
    assert result["nutrients"]["calories_kcal"] == 150.0
    assert result["nutrients"]["protein_g"] == 5.0
    assert result["health_insights"]["kind"] == "cautions"

@pytest.mark.parametrize("missing_field", [
    "energy_kcal", "protein_g", "fat_g", "carbohydrates_g", "sugar_g"
])
def test_label_validation_missing_core(missing_field):
    from app.services.scan_orchestrator import handle_label_validation
    fields = {"energy_kcal": "150", "protein_g": "5", "fat_g": "2", "carbohydrates_g": "20", "sugar_g": "15"}
    del fields[missing_field]
    req = LabelValidationRequest(raw_fields=fields)
    result = handle_label_validation(req)
    assert result["status"] == "ocr_validation_failed"
    assert missing_field in result["missing_fields"]

def test_label_validation_invalid_value():
    from app.services.scan_orchestrator import handle_label_validation
    req = LabelValidationRequest(
        raw_fields={"energy_kcal": "lots", "protein_g": "5", "fat_g": "2", "carbohydrates_g": "20", "sugar_g": "15"}
    )
    result = handle_label_validation(req)
    assert result["status"] == "ocr_validation_failed"
    assert "energy_kcal" in result["missing_fields"]

def test_label_validation_no_fabrication():
    from app.services.scan_orchestrator import handle_label_validation
    req = LabelValidationRequest(
        raw_fields={"energy_kcal": "150", "protein_g": "5", "fat_g": "2", "carbohydrates_g": "20", "sugar_g": "15"}
    )
    result = handle_label_validation(req)
    assert result["status"] == "nutrition_result"
    assert result["nutrients"]["fiber_g"] is None
    assert result["nutrients"]["sodium_mg"] is None
    assert result["food_name"] is None

def test_api_validation_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    resp = client.post("/scan/label/validate", json={
        "raw_fields": {"energy_kcal": "150", "protein_g": "5", "fat_g": "2", "carbohydrates_g": "20", "sugar_g": "15"},
        "serving_basis": "1 serving",
        "product_guess": "Box"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "nutrition_result"
    assert data["nutrients"]["calories_kcal"] == 150.0

