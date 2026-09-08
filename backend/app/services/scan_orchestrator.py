"""Scan orchestrator — coordinates the full scan pipeline."""

from fastapi import UploadFile

from app.contracts.scan_contract import FoodType, ScanResponse
from app.services.image_validation import validate_image
from app.services.photo_privacy import strip_metadata
from app.services.food_recognition import recognize_food
from app.services.label_ocr import extract_label_text
from app.services.nutrition_lookup import lookup_nutrition


class ScanOrchestrator:
    """Orchestrates the end-to-end food scanning pipeline."""

    async def process(self, image: UploadFile) -> ScanResponse:
        """
        Full pipeline:
        1. Validate the uploaded image
        2. Strip privacy-sensitive metadata
        3. Recognize the food / detect label
        4. If packaged → OCR the label
        5. Look up nutritional data
        6. Return unified response
        """
        # Step 1: Validate
        image_bytes = await validate_image(image)

        # Step 2: Strip metadata
        clean_bytes = strip_metadata(image_bytes)

        # Step 3: Recognize food
        recognition = await recognize_food(clean_bytes)

        # Step 4: OCR if packaged
        ingredients: list[str] = []
        serving_size: str | None = None
        if recognition["food_type"] == FoodType.PACKAGED:
            label_data = await extract_label_text(clean_bytes)
            ingredients = label_data["ingredients"]
            serving_size = label_data["serving_size"]

        # Step 5: Nutrition lookup
        nutrition = await lookup_nutrition(recognition["food_name"])

        # Step 6: Build response
        return ScanResponse(
            food_name=recognition["food_name"],
            food_type=recognition["food_type"],
            serving_size=serving_size,
            calories=nutrition["calories"],
            nutrients=nutrition["nutrients"],
            ingredients=ingredients,
            confidence=recognition["confidence"],
        )
