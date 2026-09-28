"""Urban analytics dashboard endpoint."""

from fastapi import APIRouter

from app.schemas.models import AnalyticsResponse
from app.services import spatial

router = APIRouter(prefix="/api", tags=["Analytics"])


@router.get("/analytics", response_model=AnalyticsResponse,
            summary="Urban statistics and chart datasets")
def analytics() -> dict:
    return spatial.analytics()
