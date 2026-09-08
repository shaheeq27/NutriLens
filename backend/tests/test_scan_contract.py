"""
Tests for backend/app/contracts/scan_contract.py.

Path in repo: backend/tests/test_scan_contract.py
"""

import pytest
from pydantic import TypeAdapter, ValidationError

from app.contracts.scan_contract import ScanResponse

adapter = TypeAdapter(ScanResponse)

VALID_SAMPLES: dict[str, dict] = {
    "image_rejected": {"status": "image_rejected", "reason": "file_too_large"},
    "no_food_detected": {"status": "no_food_detected"},
    "raw_food_detected": {
        "status": "raw_food_detected",
        "food_name": "banana",
        "candidates": [{"food_name": "plantain", "confidence": 0.2}],
        "suggested_quantity": {"amount": 1, "unit": "medium"},
    },
    "package_detected": {"status": "package_detected", "product_guess": "protein bar"},
    "label_ocr_extracted": {
        "status": "label_ocr_extracted",
        "raw_fields": {"calories": "210"},
    },
    "ocr_validation_failed": {
        "status": "ocr_validation_failed",
        "reason": "incomplete",
        "missing_fields": ["protein_g"],
    },
    "nutrition_result": {
        "status": "nutrition_result",
        "food_name": "banana",
        "quantity": {"amount": 118, "unit": "g"},
        "nutrients": {
            "calories_kcal": 105,
            "protein_g": 1.3,
            "carbohydrates_g": 27,
            "fat_g": 0.4,
        },
        "source": {
            "source": "usda",
            "fdc_id": "173944",
            "usda_description": "Bananas, raw",
        },
    },
    "nutrition_not_found": {
        "status": "nutrition_not_found",
        "food_name": "dragonfruit smoothie",
    },
    "error": {"status": "error", "message": "vendor timeout", "retryable": True},
}


@pytest.mark.parametrize("status,payload", VALID_SAMPLES.items())
def test_valid_state_round_trips(status: str, payload: dict) -> None:
    obj = adapter.validate_python(payload)
    assert obj.status == status
    dumped = adapter.dump_python(obj)
    assert dumped["status"] == status


def test_unknown_field_rejected() -> None:
    with pytest.raises(ValidationError):
        adapter.validate_python({"status": "no_food_detected", "extra_junk": "nope"})


def test_missing_discriminator_rejected() -> None:
    with pytest.raises(ValidationError):
        adapter.validate_python({"food_name": "banana"})


def test_unknown_status_rejected() -> None:
    with pytest.raises(ValidationError):
        adapter.validate_python({"status": "not_a_real_status"})


def test_usda_and_label_fields_cannot_mix() -> None:
    """The core rule: a usda-sourced result can never carry label-only
    fields (or vice versa) — this is what makes raw-food and packaged-food
    provenance mutually exclusive at the type level, not just convention."""
    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "status": "nutrition_result",
                "food_name": "banana",
                "quantity": {"amount": 118, "unit": "g"},
                "nutrients": {
                    "calories_kcal": 105,
                    "protein_g": 1.3,
                    "carbohydrates_g": 27,
                    "fat_g": 0.4,
                },
                "source": {
                    "source": "usda",
                    "fdc_id": "173944",
                    "usda_description": "Bananas, raw",
                    "ocr_confidence": 0.9,  # label-only field, must be rejected
                },
            }
        )


def test_nutrition_result_requires_source() -> None:
    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "status": "nutrition_result",
                "food_name": "banana",
                "quantity": {"amount": 118, "unit": "g"},
                "nutrients": {
                    "calories_kcal": 105,
                    "protein_g": 1.3,
                    "carbohydrates_g": 27,
                    "fat_g": 0.4,
                },
            }
        )


def test_candidates_list_bounded() -> None:
    too_many = [{"food_name": f"item{i}", "confidence": 0.1} for i in range(6)]
    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "status": "raw_food_detected",
                "food_name": "banana",
                "candidates": too_many,
                "suggested_quantity": {"amount": 1, "unit": "medium"},
            }
        )


def test_negative_nutrient_value_rejected() -> None:
    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "status": "nutrition_result",
                "food_name": "banana",
                "quantity": {"amount": 118, "unit": "g"},
                "nutrients": {
                    "calories_kcal": -5,
                    "protein_g": 1.3,
                    "carbohydrates_g": 27,
                    "fat_g": 0.4,
                },
                "source": {
                    "source": "usda",
                    "fdc_id": "173944",
                    "usda_description": "Bananas, raw",
                },
            }
        )
