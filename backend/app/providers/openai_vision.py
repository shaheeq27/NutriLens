"""
NutriLens backend — OpenAI vision provider.

Identifies whether an uploaded photo shows a raw food item, a packaged
product, or neither — and for a raw food, names it with a confidence
level and a suggested portion. This provider NEVER returns nutrition
numbers; per the project's one non-negotiable rule, nutrition always
comes from USDA FoodData Central (raw food) or OCR'd label text
(packaged food), never from the vision model.

Deliberately self-contained: defines its own result types rather than
importing from app.contracts.scan_contract (still unresolved as of this
writing). Takes credentials as constructor parameters rather than
reading environment variables directly, so it has no dependency on the
.env.example naming conflict either — whoever finishes core/config.py
wires the real value into the constructor from one place.

`model` is a REQUIRED constructor parameter with no hardcoded default.
OpenAI's vision-capable model lineup changes over time; rather than bake
in a name that might already be stale by the time this runs, that choice
is pushed to whoever deploys this, informed by current OpenAI docs at
deployment time.

The request shape below was checked against the actual installed SDK
(openai==3.8.0, pinned in requirements.txt) rather than assumed from
memory or from documentation of uncertain vintage: the image content-part
shape and the `response_format={"type": "json_schema", ...}` structured-
output shape were both verified directly against
openai.types.chat.* source in that installed version.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, ValidationError


class VisionProviderError(Exception):
    """Raised when the vision provider fails to produce a usable result —
    a network/API error, or a response that doesn't validate against the
    expected shape."""


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
    confidence: Optional[str] = None  # "high" | "medium" | "low"
    suggested_portion_label: Optional[str] = None
    suggested_portion_grams: Optional[float] = None
    candidate_food_names: tuple[str, ...] = ()
    detected_food_names: tuple[str, ...] = ()


@runtime_checkable
class VisionProvider(Protocol):
    def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionRecognitionResult: ...


class MockVisionProvider:
    """Returns a fixed, caller-supplied result regardless of input image.
    This is what 'mock providers first' actually means in code: the rest
    of the app (food_recognition.py, tests) can exercise every outcome
    without any real API key or network access."""

    def __init__(self, canned_result: VisionRecognitionResult):
        self._canned_result = canned_result

    def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionRecognitionResult:
        return self._canned_result


# ---------------------------------------------------------------------------
# OpenAI-backed implementation
# ---------------------------------------------------------------------------

_JSON_SCHEMA: dict[str, Any] = {
    "name": "food_photo_recognition",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "outcome": {
                "type": "string",
                "enum": [o.value for o in DetectionOutcome],
            },
            "food_name": {"type": ["string", "null"]},
            "confidence": {"type": ["string", "null"], "enum": ["high", "medium", "low", None]},
            "suggested_portion_label": {"type": ["string", "null"]},
            "suggested_portion_grams": {"type": ["number", "null"]},
            "candidate_food_names": {"type": "array", "items": {"type": "string"}},
            "detected_food_names": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "outcome", "food_name", "confidence", "suggested_portion_label",
            "suggested_portion_grams", "candidate_food_names", "detected_food_names",
        ],
        "additionalProperties": False,
    },
}

_SYSTEM_PROMPT = (
    "You identify food in photos for a nutrition-scanning app. You NEVER "
    "estimate or invent nutrition values (calories, protein, etc) — you only "
    "identify what the food is. Rules:\n"
    "- If the photo shows exactly one raw/minimally-processed food item "
    "(fruit, vegetable, meat, fish, egg, dairy, grain, legume, nut), set "
    "outcome to 'raw_food', name it, rate your confidence, and suggest a "
    "typical portion.\n"
    "- If your confidence is anything less than fairly sure, set outcome to "
    "'low_confidence' instead and list plausible candidate names.\n"
    "- If the photo shows more than one distinct food item, set outcome to "
    "'multiple_foods' and list what you see.\n"
    "- If the photo shows a packaged/branded product with a label, set "
    "outcome to 'package'.\n"
    "- If no food is identifiable at all, set outcome to 'no_food_detected'.\n"
    "Leave fields that don't apply to the chosen outcome as null or empty lists."
)


class _RecognitionResponse(BaseModel):
    """Validates the raw JSON the model returns before any of it is trusted.

    Every field is required (no defaults) even though several are
    nullable — this mirrors the JSON schema's "required" list as a real,
    independent safety net rather than assuming OpenAI's strict mode
    always enforces its own contract perfectly."""

    model_config = ConfigDict(extra="forbid")

    outcome: DetectionOutcome
    food_name: Optional[str]
    confidence: Optional[str]
    suggested_portion_label: Optional[str]
    suggested_portion_grams: Optional[float]
    candidate_food_names: list[str]
    detected_food_names: list[str]


def _to_data_uri(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


class OpenAIVisionProvider:
    """Real implementation. `client` can be injected for testing — see
    test_openai_vision.py, which never touches the network."""

    def __init__(self, api_key: str, model: str, client: Any = None):
        if not model:
            raise ValueError(
                "model is required and has no hardcoded default — check current "
                "OpenAI vision-capable model names before setting this."
            )
        if client is not None:
            self._client = client
        else:
            import openai  # imported lazily so MockVisionProvider users don't need this installed

            self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def recognize_food(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionRecognitionResult:
        data_uri = _to_data_uri(image_bytes, mime_type)

        # Broad except is intentional here: this is a boundary adapter around
        # a third-party SDK, and every failure mode (network, auth, rate
        # limit, timeout, SDK-internal error) should normalize to the same
        # VisionProviderError for callers to handle uniformly.
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Identify the food in this photo."},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    },
                ],
                response_format={"type": "json_schema", "json_schema": _JSON_SCHEMA},
            )
        except Exception as exc:
            raise VisionProviderError(f"OpenAI vision request failed: {exc}") from exc

        raw_text = response.choices[0].message.content
        if raw_text is None:
            raise VisionProviderError("OpenAI response had no content.")

        try:
            parsed = json.loads(raw_text)
            validated = _RecognitionResponse.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise VisionProviderError(f"OpenAI response did not match the expected shape: {exc}") from exc

        return VisionRecognitionResult(
            outcome=validated.outcome,
            food_name=validated.food_name,
            confidence=validated.confidence,
            suggested_portion_label=validated.suggested_portion_label,
            suggested_portion_grams=validated.suggested_portion_grams,
            candidate_food_names=tuple(validated.candidate_food_names),
            detected_food_names=tuple(validated.detected_food_names),
        )