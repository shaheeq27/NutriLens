"""
NutriLens backend — health check route.

A liveness/readiness endpoint for Cloud Run and uptime monitoring. Has no
dependency on the scan contract, providers, or config — intentionally
the simplest possible route, so it can be wired into main.py immediately
even while the scan route stays blocked.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
