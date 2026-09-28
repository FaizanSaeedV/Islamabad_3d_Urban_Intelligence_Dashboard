"""OSRM routing client (public demo server, OSM road network).

The demo server is rate-limited and offers no SLA - acceptable for a
portfolio/demonstration deployment; self-host OSRM for production use.
Durations are free-flow estimates without live traffic.
"""

import httpx

from app.core.config import get_settings


class RoutingError(Exception):
    """Raised when the routing engine cannot produce a route."""


async def route(lon1: float, lat1: float, lon2: float, lat2: float) -> dict:
    """Driving route between two points. Returns distance, duration, GeoJSON geometry."""
    settings = get_settings()
    url = (
        f"{settings.osrm_base_url}/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}"
    )
    params = {"overview": "full", "geometries": "geojson", "alternatives": "false"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RoutingError(f"OSRM returned no route (code={payload.get('code')})")

    best = payload["routes"][0]
    return {
        "distance_m": round(best["distance"], 1),
        "duration_s": round(best["duration"], 1),
        "geometry": best["geometry"],  # GeoJSON LineString (EPSG:4326)
    }
