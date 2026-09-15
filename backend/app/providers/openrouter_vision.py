import base64
import json
import httpx
from typing import Optional
from app.providers.vision import (
    VisionProvider, VisionRecognitionResult, DetectionOutcome,
    VisionProviderError, VisionProviderRecoverableError, VisionProviderAuthError
)
from app.providers.llm_vision_prompt import SYSTEM_PROMPT

class OpenRouterVisionProvider(VisionProvider):
    def __init__(self, api_key: str, model_id: str = "google/gemma-4-31b-it:free", http_client: Optional[httpx.Client] = None):
        if not api_key:
            raise VisionProviderAuthError("OpenRouter API key is required")
        self.api_key = api_key
        self.model_id = model_id
        self.client = http_client or httpx.Client(timeout=15.0)

    def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionRecognitionResult:
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        
        payload = {
            "model": self.model_id,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this image and return the JSON."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded_image}"
                            }
                        }
                    ]
                }
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://nutrilens.app",
            "X-Title": "NutriLens",
        }
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        try:
            resp = self.client.post(url, headers=headers, json=payload)
            if resp.status_code in (401, 403):
                raise VisionProviderAuthError(f"OpenRouter authentication failed: {resp.status_code}")
            if resp.status_code in (429, 500, 502, 503, 504):
                raise VisionProviderRecoverableError(f"OpenRouter recoverable error: {resp.status_code}")
            resp.raise_for_status()
            
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            
            text = text.strip(); text = text[7:-3] if text.startswith("```json") else text; text = text.strip("`"); parsed = json.loads(text)
            
            outcome_str = parsed.get("outcome", "").lower()
            try:
                outcome = DetectionOutcome(outcome_str)
            except ValueError:
                return VisionRecognitionResult(outcome=DetectionOutcome.LOW_CONFIDENCE)
                
            return VisionRecognitionResult(
                outcome=outcome,
                food_name=parsed.get("food_name"),
                product_guess=parsed.get("product_guess"),
            )
            
        except httpx.TimeoutException as exc:
            raise VisionProviderRecoverableError(f"OpenRouter timeout: {exc}") from exc
        except httpx.NetworkError as exc:
            raise VisionProviderRecoverableError(f"OpenRouter network error: {exc}") from exc
        except VisionProviderError:
            raise
        except Exception as exc:
            raise VisionProviderError(f"OpenRouter unexpected error: {exc}") from exc
