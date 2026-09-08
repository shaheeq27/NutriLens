"""Food recognition service — identifies food items in images using AI."""

from app.contracts.scan_contract import FoodType


async def recognize_food(image_bytes: bytes) -> dict:
    """
    Analyze an image to identify the food item and its type.

    Returns a dict with:
      - food_name: str
      - food_type: FoodType
      - confidence: float
    """
    # TODO: Integrate with Gemini Vision API for actual recognition
    return {
        "food_name": "Unknown Food",
        "food_type": FoodType.UNKNOWN,
        "confidence": 0.0,
    }
