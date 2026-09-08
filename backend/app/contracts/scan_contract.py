"""
Source of truth for the NutriLens scanning API.
Defines a 9-state discriminated union for the scan result, ensuring strict validation,
fixed-field nutrition (no duplicate sources of truth), explicit nullables, 
and structural enforcement of provenance.
"""

from typing import Annotated, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model enforcing no unknown fields globally."""
    model_config = ConfigDict(extra="forbid")


# -----------------------------------------------------------------------------
# 1. Image Rejected
# -----------------------------------------------------------------------------
ImageRejectReason = Literal[
    "file_too_large",
    "invalid_format",
    "corrupt_file",
    "dimensions_out_of_bounds",
    "timeout"
]

class ImageRejected(StrictModel):
    status: Literal["image_rejected"] = "image_rejected"
    reason: ImageRejectReason


# -----------------------------------------------------------------------------
# 2. No Food Detected
# -----------------------------------------------------------------------------
class NoFoodDetected(StrictModel):
    status: Literal["no_food_detected"] = "no_food_detected"


# -----------------------------------------------------------------------------
# 3. Raw Food Detected
# -----------------------------------------------------------------------------
class RawFoodDetected(StrictModel):
    status: Literal["raw_food_detected"] = "raw_food_detected"
    food_name: str = Field(..., max_length=255)
    suggested_quantity: str = Field(..., max_length=100)
    candidates: list[str] = Field(..., max_length=5)


# -----------------------------------------------------------------------------
# 4. Package Detected
# -----------------------------------------------------------------------------
class PackageDetected(StrictModel):
    status: Literal["package_detected"] = "package_detected"


# -----------------------------------------------------------------------------
# 5. Label OCR Extracted
# -----------------------------------------------------------------------------
class LabelOcrExtracted(StrictModel):
    status: Literal["label_ocr_extracted"] = "label_ocr_extracted"
    raw_text_snippet: Optional[str] = Field(None, max_length=1000)


# -----------------------------------------------------------------------------
# 6. OCR Validation Failed
# -----------------------------------------------------------------------------
class OcrValidationFailed(StrictModel):
    status: Literal["ocr_validation_failed"] = "ocr_validation_failed"
    missing_fields: list[str] = Field(..., max_length=20)


# -----------------------------------------------------------------------------
# 7. Nutrition Result (with nested discriminated union for source)
# -----------------------------------------------------------------------------
class UsdaSource(StrictModel):
    type: Literal["usda"] = "usda"
    fdc_id: str = Field(..., max_length=50)
    usda_description: str = Field(..., max_length=255)

class LabelSource(StrictModel):
    type: Literal["label"] = "label"
    ocr_confidence: float = Field(..., ge=0.0, le=1.0)

NutritionSource = Annotated[
    UsdaSource | LabelSource, 
    Field(discriminator="type")
]

class NutritionResult(StrictModel):
    status: Literal["nutrition_result"] = "nutrition_result"
    food_name: str = Field(..., max_length=255)
    serving_size: Optional[str] = Field(None, max_length=100)
    
    # Fixed field set for nutrition to prevent duplicate sources of truth
    calories: Optional[float] = Field(None, ge=0.0)
    protein_g: Optional[float] = Field(None, ge=0.0)
    carbs_g: Optional[float] = Field(None, ge=0.0)
    fat_g: Optional[float] = Field(None, ge=0.0)
    
    source: NutritionSource


# -----------------------------------------------------------------------------
# 8. Nutrition Not Found
# -----------------------------------------------------------------------------
class NutritionNotFound(StrictModel):
    status: Literal["nutrition_not_found"] = "nutrition_not_found"
    item_name: str = Field(..., max_length=100)


# -----------------------------------------------------------------------------
# 9. Error
# -----------------------------------------------------------------------------
class ScanError(StrictModel):
    status: Literal["error"] = "error"
    message: str = Field(..., max_length=500)
    retryable: bool


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
