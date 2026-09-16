import base64
import httpx
import time
from typing import Optional
from app.providers.vision import (
    VisionProvider, VisionRecognitionResult, DetectionOutcome,
    VisionProviderError, VisionProviderRecoverableError, VisionProviderAuthError
)
from app.providers.llm_vision_prompt import SYSTEM_PROMPT

class GeminiVisionProvider(VisionProvider):
    def __init__(self, api_key: str, http_client: Optional[httpx.Client] = None):
        if not api_key:
            raise VisionProviderAuthError("Gemini API key is required")
        self.api_key = api_key
        self.client = http_client or httpx.Client(timeout=60.0)

    def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionRecognitionResult:
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')

        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "parts": [
                        {"inlineData": {"mimeType": mime_type, "data": encoded_image}},
                        {"text": "Analyze this image and return the JSON."}
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={self.api_key}"

        try:
            resp = self.client.post(url, json=payload)

            if resp.status_code >= 400:
                sanitized_url = url.replace(self.api_key, "REDACTED")
                print(f"Gemini API Error [{resp.status_code}] at {sanitized_url}")
                try:
                    print(f"Response Body: {resp.json()}")
                except Exception:
                    print(f"Response Body: {resp.text}")

            if resp.status_code in (400, 401, 403):
                # Do NOT fallback for malformed request or auth errors.
                if resp.status_code in (401, 403):
                    raise VisionProviderAuthError(f"Gemini authentication failed: {resp.status_code}")
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as e:
                    sanitized_msg = str(e).replace(self.api_key, "REDACTED")
                    raise VisionProviderError(f"Gemini HTTP error: {sanitized_msg}") from None

            if resp.status_code in (429, 500, 502, 503, 504):
                raise VisionProviderRecoverableError(f"Gemini recoverable error: {resp.status_code}")

            # Sanitize any unexpected HTTPStatusError just in case
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                sanitized_msg = str(e).replace(self.api_key, "REDACTED")
                raise VisionProviderError(f"Gemini HTTP error: {sanitized_msg}") from None

            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]

            import json
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

        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise VisionProviderRecoverableError(f"Gemini network error: {exc}") from exc
        except VisionProviderError:
            raise
        except Exception as exc:
            sanitized_msg = str(exc).replace(self.api_key, "REDACTED")
            raise VisionProviderError(f"Gemini unexpected error: {sanitized_msg}") from None
