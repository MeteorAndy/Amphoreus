"""API v1 router placeholder."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/status")
async def api_status():
    """Lightweight API status endpoint."""
    return {"api_version": "v1", "status": "operational"}