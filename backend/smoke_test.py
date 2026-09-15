import asyncio
from app.providers.vision import VisionManager
from app.providers.gemini_vision import GeminiVisionProvider
from app.providers.openrouter_vision import OpenRouterVisionProvider
from app.core.config import get_settings

def run_tests():
    settings = get_settings()
    gemini = GeminiVisionProvider(api_key=settings.gemini_api_key)
    openrouter = OpenRouterVisionProvider(api_key=settings.openrouter_api_key, model_id=settings.openrouter_vision_model)
    manager = VisionManager(primary=gemini, fallback=openrouter)

    with open("fixtures/raw-food/banana.jpg", "rb") as f:
        banana_bytes = f.read()
    
    print("\n--- VISION MANAGER BANANA TEST (WITH FALLBACK) ---")
    try:
        res = manager.recognize_food(banana_bytes)
        print("HTTP Status: SUCCESS")
        print("Outcome:", res.outcome)
        print("Food Name:", getattr(res, 'food_name', None))
        print("Product Guess:", getattr(res, 'product_guess', None))
        print("Valid JSON: YES")
        print("No Nutrition Generated:", "YES" if not hasattr(res, 'calories') else "NO")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    run_tests()
