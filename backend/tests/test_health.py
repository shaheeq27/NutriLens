"""
Test for backend/app/api/routes/health.py.
Run with: pytest test_health.py -v
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from health import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_health_check_returns_200_and_ok_status():
    response = _client().get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
