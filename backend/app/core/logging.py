"""
Logging configuration.

Per README's architecture rules: raw image bytes and raw OCR text must
never be logged. Callers should never pass these in the first place —
this module's filter is a defense-in-depth backstop, not a substitute for
that discipline.

Path in repo: backend/app/core/logging.py
"""

from __future__ import annotations

import logging
import sys

_REDACTED = "[REDACTED: raw image/OCR payload must not be logged]"

# Any log record with one of these attributes has its value scrubbed
# before formatting/output, regardless of what the caller passed.
_FORBIDDEN_EXTRA_KEYS = {"raw_image_bytes", "raw_ocr_text", "image_data"}


class RedactSensitiveFieldsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key in _FORBIDDEN_EXTRA_KEYS:
            if hasattr(record, key):
                setattr(record, key, _REDACTED)
        return True


def configure_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("nutrilens")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        handler.addFilter(RedactSensitiveFieldsFilter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


# Import-and-use logger for the common case: `from app.core.logging import logger`
logger = configure_logging()
