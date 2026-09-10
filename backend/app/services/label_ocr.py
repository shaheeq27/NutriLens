"""
NutriLens backend — label OCR service.

Composes image_validation, photo_privacy, and an OcrProvider into the
packaged-food label step of the scan flow: validate the upload, strip
its EXIF metadata, run OCR, then parse the raw extracted text into
nutrient fields the user can review.

Parsing raw OCR text into structured values is inherently approximate —
labels vary wildly in layout. This module is deliberately conservative:
it extracts a value only when a line matches an expected nutrient label
followed by a number, and it reports what it could NOT find rather than
guessing. Anything not confidently extracted is left absent, matching
the project rule that packaged-food nutrition must come from the label,
not be inferred.

Deliberately self-contained: no import from app.contracts.scan_contract
(still unresolved), no environment reads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.providers.google_vision import OcrProvider, OcrProviderError, OcrRejection, OcrRejectionReason, OcrResult
from app.services.image_validation import ImageValidationError, validate_image_upload
from app.services.photo_privacy import strip_exif

# The nutrient fields this service knows how to look for, and the
# regex patterns (case-insensitive) used to find each one. Patterns
# match a label phrase followed by a number, optionally with a unit;
# the first matching pattern per field wins.
_FIELD_PATTERNS: dict[str, list[str]] = {
    "energy_kcal": [
        r"calories?\s*[:\-]?\s*(\d+(?:\.\d+)?)",
        r"energy\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*kcal",
    ],
    "protein_g": [r"protein\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*g"],
    "carbohydrates_g": [
        r"total\s+carbohydrate[s]?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*g",
        r"carbohydrate[s]?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*g",
    ],
    "fat_g": [
        r"total\s+fat\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*g",
        r"fat\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*g",
    ],
    "fiber_g": [r"(?:dietary\s+)?fiber\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*g"],
    "sugar_g": [r"(?:total\s+)?sugars?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*g"],
    "sodium_mg": [r"sodium\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*mg"],
    "potassium_mg": [r"potassium\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*mg"],
    "caffeine_mg": [r"caffeine\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*mg"],
}

# Core four — if none of these are found at all, the label likely wasn't
# a nutrition panel, or OCR quality was too poor to trust anything else.
_CORE_FIELDS = ("energy_kcal", "protein_g", "carbohydrates_g", "fat_g")

_SERVING_BASIS_PATTERN = re.compile(
    r"(?:per\s+serving|serving\s+size)\s*[:\-]?\s*([\d.]+\s*(?:g|ml|oz))", re.IGNORECASE
)


class LabelExtractionOutcome(str, Enum):
    EXTRACTED = "extracted"
    INVALID_IMAGE = "invalid_image"
    NO_TEXT_DETECTED = "no_text_detected"
    NOT_A_NUTRITION_LABEL = "not_a_nutrition_label"
    PROVIDER_ERROR = "provider_error"


@dataclass(frozen=True)
class LabelExtractionResult:
    outcome: LabelExtractionOutcome
    serving_basis: Optional[str] = None
    extracted: Optional[dict[str, float]] = None
    missing_fields: tuple[str, ...] = ()
    message: Optional[str] = None


def extract_label_nutrients(image_bytes: bytes, ocr_provider: OcrProvider) -> LabelExtractionResult:
    """The actual composed step: validate -> strip EXIF -> OCR -> parse."""
    validation_result = validate_image_upload(image_bytes)
    if isinstance(validation_result, ImageValidationError):
        return LabelExtractionResult(
            outcome=LabelExtractionOutcome.INVALID_IMAGE,
            message=validation_result.message,
        )

    cleaned_bytes = strip_exif(validation_result.data)

    try:
        ocr_outcome = ocr_provider.extract_text(cleaned_bytes)
    except OcrProviderError as exc:
        return LabelExtractionResult(
            outcome=LabelExtractionOutcome.PROVIDER_ERROR,
            message=str(exc),
        )

    if isinstance(ocr_outcome, OcrRejection):
        # Only reason OcrProvider ever produces today, but mapped
        # explicitly rather than assumed 1:1 in case that changes.
        if ocr_outcome.reason == OcrRejectionReason.NO_TEXT_DETECTED:
            return LabelExtractionResult(
                outcome=LabelExtractionOutcome.NO_TEXT_DETECTED, message=ocr_outcome.message
            )
        return LabelExtractionResult(outcome=LabelExtractionOutcome.PROVIDER_ERROR, message=ocr_outcome.message)

    return _parse_label_text(ocr_outcome.raw_text)


def _parse_label_text(raw_text: str) -> LabelExtractionResult:
    lowered = raw_text.lower()

    extracted: dict[str, float] = {}
    for field, patterns in _FIELD_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                extracted[field] = float(match.group(1))
                break

    if not any(field in extracted for field in _CORE_FIELDS):
        return LabelExtractionResult(
            outcome=LabelExtractionOutcome.NOT_A_NUTRITION_LABEL,
            message="This doesn't look like a nutrition label — no calorie, protein, carb, or fat values were found.",
        )

    serving_match = _SERVING_BASIS_PATTERN.search(lowered)
    serving_basis = f"Per {serving_match.group(1)} serving" if serving_match else None

    missing = tuple(f for f in _FIELD_PATTERNS if f not in extracted)

    return LabelExtractionResult(
        outcome=LabelExtractionOutcome.EXTRACTED,
        serving_basis=serving_basis,
        extracted=extracted,
        missing_fields=missing,
    )