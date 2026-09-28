"""Weather endpoint (Open-Meteo proxy with short cache)."""

import httpx
from fastapi import APIRouter, HTTPException

from app.schemas.models import WeatherResponse
from app.services import weather

router = APIRouter(prefix="/api", tags=["Weather"])


@router.get("/weather", response_model=WeatherResponse,
            summary="Current weather in Islamabad (Open-Meteo)")
async def current_weather() -> dict:
    try:
        return await weather.current_weather()
    except (httpx.HTTPError, OSError, ImportError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Weather service unavailable: {exc}") from exc
