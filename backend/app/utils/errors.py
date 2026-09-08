"""
Domain exceptions for the backend.

These represent internal failure modes. The API layer / orchestrator is
responsible for catching them and translating them into the matching
contract state (see app.contracts.scan_contract) rather than letting them
leak out as raw, undifferentiated 500s.

Path in repo: backend/app/utils/errors.py
"""

from __future__ import annotations


class NutriLensError(Exception):
    """Base class for every domain-specific error in this app."""


class ImageValidationError(NutriLensError):
    """Raised when an uploaded image fails validation before any vendor
    API call is made. `reason` should match one of the `ImageRejected`
    `reason` literals in the scan contract."""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = reason
        super().__init__(detail or reason)


class ProviderError(NutriLensError):
    """Raised when an external vendor call (OpenAI, Google Vision, USDA)
    fails. `retryable` mirrors `ScanError.retryable` in the contract, so
    the caller doesn't have to re-derive it from the message text."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        self.retryable = retryable
        super().__init__(message)


class OcrValidationError(NutriLensError):
    """Raised when OCR output fails validation. `reason` should match one
    of `OcrValidationFailed.reason`; `missing_fields` mirrors the contract
    field of the same name."""

    def __init__(self, reason: str, missing_fields: list[str] | None = None) -> None:
        self.reason = reason
        self.missing_fields = missing_fields or []
        super().__init__(reason)


class NutritionNotFoundError(NutriLensError):
    """Raised when a raw food is identified but has no USDA match. Must
    never be silently swallowed into an estimated nutrition value — see
    the README's core rule."""

    def __init__(self, food_name: str) -> None:
        self.food_name = food_name
        super().__init__(f"No USDA match for: {food_name}")
