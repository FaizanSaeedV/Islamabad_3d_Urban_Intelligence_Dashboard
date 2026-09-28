"""Open-Meteo weather client (free, keyless, CC BY 4.0) with a short cache."""

import time
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings

CACHE_TTL_S = 300  # Open-Meteo updates ~every 15 min; 5 min cache is polite
_cache: dict = {"data": None, "at": 0.0}

CURRENT_FIELDS = (
    "temperature_2m,relative_humidity_2m,precipitation,rain,"
    "cloud_cover,wind_speed_10m,wind_direction_10m,weather_code,is_day"
)

ISLAMABAD_LAT = 33.6844
ISLAMABAD_LON = 73.0479


async def current_weather() -> dict:
    """Current conditions for Islamabad. Raises httpx.HTTPError on upstream failure."""
    now = time.time()
    if _cache["data"] and now - _cache["at"] < CACHE_TTL_S:
        return _cache["data"]

    settings = get_settings()
    url = f"{settings.open_meteo_base_url}/forecast"
    params = {
        "latitude": ISLAMABAD_LAT,
        "longitude": ISLAMABAD_LON,
        "current": CURRENT_FIELDS,
        "timezone": "Asia/Karachi",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    current = payload.get("current", {})
    data = {
        "latitude": payload.get("latitude", ISLAMABAD_LAT),
        "longitude": payload.get("longitude", ISLAMABAD_LON),
        "temperature_c": current.get("temperature_2m"),
        "humidity_pct": current.get("relative_humidity_2m"),
        "precipitation_mm": current.get("precipitation"),
        "rain_mm": current.get("rain"),
        "cloud_cover_pct": current.get("cloud_cover"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "wind_direction_deg": current.get("wind_direction_10m"),
        "weather_code": current.get("weather_code"),
        "is_day": bool(current.get("is_day")) if current.get("is_day") is not None else None,
        "fetched_at": datetime.now(timezone.utc),
    }
    _cache.update(data=data, at=now)
    return data
