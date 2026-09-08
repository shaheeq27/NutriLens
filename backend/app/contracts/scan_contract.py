"""
Source of truth for the NutriLens scanning API.
Defines a 9-state discriminated union for the scan result, ensuring strict validation,
bounded fields, explicit nullables, and structural enforcement of provenance.
"""

from typing import Annotated, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class BaseContract(BaseModel):
    """Base model enforcing no unknown fields globally."""
    model_config = ConfigDict(extra="forbid")


# -----------------------------------------------------------------------------
# 1. Image Rejected
# -----------------------------------------------------------------------------
class ImageRejected(BaseContract):
    status: Literal["image_rejected"] = "image_rejected"
    reason: str = Field(..., max_length=255)


# -----------------------------------------------------------------------------
# 2. No Food Detected
# -----------------------------------------------------------------------------
class NoFoodDetected(BaseContract):
    status: Literal["no_food_detected"] = "no_food_detected"


# -----------------------------------------------------------------------------
# 3. Raw Food Detected
# -----------------------------------------------------------------------------
class RawFoodDetected(BaseContract):
    status: Literal["raw_food_detected"] = "raw_food_detected"
    candidates: list[str] = Field(..., max_length=5)


# -----------------------------------------------------------------------------
# 4. Package Detected
# -----------------------------------------------------------------------------
class PackageDetected(BaseContract):
    status: Literal["package_detected"] = "package_detected"


# -----------------------------------------------------------------------------
# 5. Label OCR Extracted
# -----------------------------------------------------------------------------
class LabelOcrExtracted(BaseContract):
    status: Literal["label_ocr_extracted"] = "label_ocr_extracted"
    raw_text_snippet: Optional[str] = Field(None, max_length=1000)


# -----------------------------------------------------------------------------
# 6. OCR Validation Failed
# -----------------------------------------------------------------------------
class OcrValidationFailed(BaseContract):
    status: Literal["ocr_validation_failed"] = "ocr_validation_failed"
    missing_fields: list[str] = Field(..., max_length=20)


# -----------------------------------------------------------------------------
# 7. Nutrition Result (with nested discriminated union for source)
# -----------------------------------------------------------------------------
class UsdaSource(BaseContract):
    type: Literal["usda"] = "usda"
    fdc_id: str = Field(..., max_length=50)

class LabelSource(BaseContract):
    type: Literal["label"] = "label"
    ocr_confidence: float = Field(..., ge=0.0, le=1.0)

NutritionSource = Annotated[
    UsdaSource | LabelSource, 
    Field(discriminator="type")
]

class Nutrient(BaseContract):
    name: str = Field(..., max_length=100)
    amount: float = Field(..., ge=0.0)
    unit: str = Field(..., max_length=20)

class NutritionResult(BaseContract):
    status: Literal["nutrition_result"] = "nutrition_result"
    food_name: str = Field(..., max_length=255)
    calories: Optional[float] = Field(None, ge=0.0)
    serving_size: Optional[str] = Field(None, max_length=100)
    nutrients: list[Nutrient] = Field(default_factory=list, max_length=50)
    source: NutritionSource


# -----------------------------------------------------------------------------
# 8. Nutrition Not Found
# -----------------------------------------------------------------------------
class NutritionNotFound(BaseContract):
    status: Literal["nutrition_not_found"] = "nutrition_not_found"
    item_name: str = Field(..., max_length=100)


# -----------------------------------------------------------------------------
# 9. Error
# -----------------------------------------------------------------------------
class ScanError(BaseContract):
    status: Literal["error"] = "error"
    message: str = Field(..., max_length=500)


# =============================================================================
# MAIN EXPORT
# =============================================================================
ScanResponse = Annotated[
    ImageRejected
    | NoFoodDetected
    | RawFoodDetected
    | PackageDetected
    | LabelOcrExtracted
    | OcrValidationFailed
    | NutritionResult
    | NutritionNotFound
    | ScanError,
    Field(discriminator="status")
]
