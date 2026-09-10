"""
NutriLens backend — application entrypoint.

PROVISIONAL settings loading: core/config.py (Lane A's file) could not
be verified to load the right environment variables as of this writing
— last checked, it was reported to still reference a leftover
`gemini_api_key` field from an abandoned provider decision, and the real
`.env.example` content has been a moving target across this whole
project (see the earlier back-and-forth on that file). Rather than
import from core/config.py and inherit whichever of those problems is
still live, this file reads CORS_ALLOWED_ORIGINS directly with a safe
local-dev fallback. This is a placeholder — once core/config.py is
confirmed correct, settings loading here should go through it instead.

Provider wiring for api/routes/scan.py's `get_*_provider` dependencies
is intentionally left undone here too, for the same reason: doing it now
means guessing at which of the three candidate env-var naming schemes
(mine, the brief's claimed version, or whatever's actually committed) is
real. `/scan`, `/scan/raw-food`, and `/scan/label` will 500 with a clear
NotImplementedError until that's wired — everything else (routing,
CORS, /health) works now.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.scan import router as scan_router


def create_app() -> FastAPI:
    app = FastAPI(title="NutriLens API")

    origins_raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
    origins = [origin.strip() for origin in origins_raw.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(scan_router)
    return app


app = create_app()