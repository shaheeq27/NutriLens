"""Shared contracts (schemas) for the scan feature."""

from enum import Enum

from pydantic import BaseModel, Field


class FoodType(str, Enum):
    """Type of food detected in the image."""

    RAW = "raw"
    PACKAGED = "packaged"
    UNKNOWN = "unknown"


class NutrientInfo(BaseModel):
    """Nutritional information for a single nutrient."""

    name: str
    amount: float
    unit: str
    daily_value_percent: float | None = None


class ScanResponse(BaseModel):
    """Response contract for the /api/scan endpoint."""

    food_name: str
    food_type: FoodType
    serving_size: str | None = None
    calories: float | None = None
    nutrients: list[NutrientInfo] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, description="Recognition confidence 0-1")
    warnings: list[str] = Field(default_factory=list)
