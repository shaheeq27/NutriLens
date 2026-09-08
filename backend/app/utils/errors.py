"""Custom error types and HTTP exception helpers."""

from fastapi import HTTPException, status


class NutriLensError(Exception):
    """Base error for NutriLens application."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    def to_http_exception(self) -> HTTPException:
        return HTTPException(status_code=self.status_code, detail=self.message)


class ValidationError(NutriLensError):
    """Raised when image or input validation fails."""

    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class RecognitionError(NutriLensError):
    """Raised when food recognition fails."""

    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
