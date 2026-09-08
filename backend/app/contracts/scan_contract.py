"""
Scan response contract — the backend source of truth (see README's
architecture rules).

Every response from the scan endpoint is exactly ONE of the models below,
selected by the `status` field. This file is where "the vision model
identifies food, it never invents nutrition numbers" is enforced
structurally: only `NutritionResult` carries nutrient values, and its
`source` field is itself a discriminated union, so a raw-food (USDA)
result and a packaged-food (label) result are mutually exclusive at the
type level — not just two optional fields that happen to agree in practice.

frontend/src/contracts/scan_contract.ts mirrors this file exactly and is
generated to match it, never maintained independently.

Path in repo: backend/app/contracts/scan_contract.py
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base for every contract model. Unknown fields are always rejected —
    a typo or an accidental extra field should fail loudly, not pass
    through silently to the frontend."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

class Quantity(StrictModel):
    """A user-confirmed amount of food, e.g. 150 g or 1 medium."""

    amount: float = Field(gt=0, le=100_000)
    unit: str = Field(min_length=1, max_length=32)


class Nutrients(StrictModel):
    """Nutrient values for the confirmed quantity. Bounds exist to catch
    obviously-corrupt provider data before it reaches the user, not to
    encode any real nutritional ceiling."""

    calories_kcal: float = Field(ge=0, le=10_000)
    protein_g: float = Field(ge=0, le=1_000)
    carbohydrates_g: float = Field(ge=0, le=1_000)
    fat_g: float = Field(ge=0, le=1_000)
    fiber_g: Optional[float] = Field(default=None, ge=0, le=1_000)
    sugar_g: Optional[float] = Field(default=None, ge=0, le=1_000)
    sodium_mg: Optional[float] = Field(default=None, ge=0, le=100_000)


class FoodCandidate(StrictModel):
    """An alternate guess when the vision model isn't fully confident in
    its top identification."""

    food_name: str = Field(min_length=1, max_length=128)
    confidence: float = Field(ge=0, le=1)


# ---------------------------------------------------------------------------
# Nutrition source — mutually exclusive at the type level (the core rule)
# ---------------------------------------------------------------------------

class UsdaSource(StrictModel):
    source: Literal["usda"] = "usda"
    fdc_id: str = Field(min_length=1, max_length=64)
    usda_description: str = Field(min_length=1, max_length=256)


class LabelSource(StrictModel):
    source: Literal["label"] = "label"
    ocr_confidence: float = Field(ge=0, le=1)


NutritionSource = Annotated[
    Union[UsdaSource, LabelSource],
    Field(discriminator="source"),
]


# ---------------------------------------------------------------------------
# Response states — discriminated union on `status`
# ---------------------------------------------------------------------------

class ImageRejected(StrictModel):
    """Failed validation before any vendor API call was made."""

    status: Literal["image_rejected"] = "image_rejected"
    reason: Literal[
        "file_too_large",
        "unsupported_file_type",
        "invalid_magic_bytes",
        "dimensions_out_of_range",
        "megapixel_limit_exceeded",
        "decode_timeout",
    ]


class NoFoodDetected(StrictModel):
    """Vision model ran but found no identifiable food in the frame."""

    status: Literal["no_food_detected"] = "no_food_detected"


class RawFoodDetected(StrictModel):
    """Vision identified a raw food; the frontend must show a quantity
    confirmation step before any nutrition lookup happens."""

    status: Literal["raw_food_detected"] = "raw_food_detected"
    food_name: str = Field(min_length=1, max_length=128)
    candidates: list[FoodCandidate] = Field(default_factory=list, max_length=5)
    suggested_quantity: Quantity


class PackageDetected(StrictModel):
    """Image is a packaged product; the frontend must ask for a photo of
    the back/side nutrition label next."""

    status: Literal["package_detected"] = "package_detected"
    product_guess: Optional[str] = Field(default=None, max_length=128)


class LabelOcrExtracted(StrictModel):
    """OCR ran on the label photo. Fields are raw/unvalidated — this state
    exists so the orchestrator has a place to hand off to validation logic;
    it is not shown to the user as-is."""

    status: Literal["label_ocr_extracted"] = "label_ocr_extracted"
    raw_fields: dict[str, str] = Field(default_factory=dict, max_length=50)


class OcrValidationFailed(StrictModel):
    """Label was unreadable, incomplete, or internally inconsistent.
    The frontend should ask for a clearer photo — never fall back to
    guessing the missing values."""

    status: Literal["ocr_validation_failed"] = "ocr_validation_failed"
    reason: Literal["unreadable", "incomplete", "inconsistent_values"]
    missing_fields: list[str] = Field(default_factory=list, max_length=20)


class NutritionResult(StrictModel):
    """The final result page payload. Both the raw-food and packaged-food
    paths converge here. `source` determines provenance and is itself a
    discriminated union — see NutritionSource above."""

    status: Literal["nutrition_result"] = "nutrition_result"
    food_name: str = Field(min_length=1, max_length=128)
    quantity: Quantity
    nutrients: Nutrients
    source: NutritionSource


class NutritionNotFound(StrictModel):
    """Raw food was identified but has no USDA match. This is a hard stop
    — the model must never estimate values to fill the gap."""

    status: Literal["nutrition_not_found"] = "nutrition_not_found"
    food_name: str = Field(min_length=1, max_length=128)


class ScanError(StrictModel):
    """Generic or vendor-side failure not covered by a more specific state."""

    status: Literal["error"] = "error"
    message: str = Field(min_length=1, max_length=512)
    retryable: bool


ScanResponse = Annotated[
    Union[
        ImageRejected,
        NoFoodDetected,
        RawFoodDetected,
        PackageDetected,
        LabelOcrExtracted,
        OcrValidationFailed,
        NutritionResult,
        NutritionNotFound,
        ScanError,
    ],
    Field(discriminator="status"),
]
