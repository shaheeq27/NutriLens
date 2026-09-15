from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol, runtime_checkable

class VisionProviderError(Exception):
    pass

class VisionProviderRecoverableError(VisionProviderError):
    pass

class VisionProviderAuthError(VisionProviderError):
    pass

class DetectionOutcome(str, Enum):
    RAW_FOOD = "raw_food"
    PACKAGE = "package"
    NO_FOOD_DETECTED = "no_food_detected"
    LOW_CONFIDENCE = "low_confidence"
    MULTIPLE_FOODS = "multiple_foods"

@dataclass(frozen=True)
class VisionRecognitionResult:
    outcome: DetectionOutcome
    food_name: Optional[str] = None
    product_guess: Optional[str] = None
    confidence: Optional[str] = None
    candidate_food_names: tuple[str, ...] = ()
    detected_food_names: tuple[str, ...] = ()

@runtime_checkable
class VisionProvider(Protocol):
    def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionRecognitionResult: ...

class VisionManager(VisionProvider):
    def __init__(self, primary: VisionProvider, fallback: VisionProvider):
        self.primary = primary
        self.fallback = fallback

    def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionRecognitionResult:
        try:
            return self.primary.recognize_food(image_bytes, mime_type)
        except VisionProviderRecoverableError:
            return self.fallback.recognize_food(image_bytes, mime_type)
        # VisionProviderAuthError and generic VisionProviderError do not trigger fallback.
        # They will bubble up to `food_recognition.py` which maps it to PROVIDER_ERROR.

class MockVisionProvider(VisionProvider):
    def __init__(self, canned_result: VisionRecognitionResult | Exception):
        self._canned = canned_result
    
    def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionRecognitionResult:
        if isinstance(self._canned, Exception):
            raise self._canned
        return self._canned
