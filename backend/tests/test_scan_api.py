"""Integration tests for the scan API endpoint."""

import pytest
from httpx import AsyncClient, ASGITransport
from io import BytesIO
from PIL import Image

from app.main import app


def _make_test_image() -> bytes:
    """Create a minimal valid PNG image."""
    img = Image.new("RGB", (100, 100), color="green")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_health_check():
    """GET /health should return 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_scan_endpoint_accepts_image():
    """POST /api/scan with a valid image should return 200."""
    image_bytes = _make_test_image()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/scan",
            files={"image": ("test.png", BytesIO(image_bytes), "image/png")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "food_name" in data
    assert "food_type" in data
