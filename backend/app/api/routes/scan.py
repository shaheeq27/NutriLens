"""Scan API routes."""

from fastapi import APIRouter, File, UploadFile

from app.contracts.scan_contract import ScanResponse
from app.services.scan_orchestrator import ScanOrchestrator
from app.utils.errors import NutriLensError

router = APIRouter(tags=["scan"])


@router.post("/scan", response_model=ScanResponse)
async def scan_food(image: UploadFile = File(...)):
    """
    Scan a food image (raw food photo or packaged food label)
    and return nutritional information.
    """
    try:
        orchestrator = ScanOrchestrator()
        result = await orchestrator.process(image)
        return result
    except NutriLensError as e:
        raise e.to_http_exception()
