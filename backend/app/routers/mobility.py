"""Mobility & analysis endpoints: nearest facility, routing, coverage."""

from typing import Annotated

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.schemas.models import (
    CoverageResponse,
    FacilityType,
    NearestResponse,
    RouteResponse,
)
from app.services import routing, spatial

router = APIRouter(prefix="/api", tags=["Mobility & Analysis"])

# Generous validation window around the study area (northern Pakistan + margin)
LonQ = Annotated[float, Query(ge=70.0, le=75.5, description="Longitude (EPSG:4326)")]
LatQ = Annotated[float, Query(ge=31.0, le=36.5, description="Latitude (EPSG:4326)")]


@router.get("/nearest", response_model=NearestResponse,
            summary="K nearest facilities from a point")
def nearest(
    lon: LonQ,
    lat: LatQ,
    type: Annotated[FacilityType, Query(description="Facility class")],
    n: Annotated[int, Query(ge=1, le=25)] = 5,
) -> dict:
    results = spatial.nearest_facilities(lon, lat, type, n)
    return {
        "origin": {"lon": lon, "lat": lat},
        "facility_type": type,
        "results": results,
    }


@router.get("/route", response_model=RouteResponse,
            summary="Network route between two points (OSRM)")
async def get_route(from_lon: LonQ, from_lat: LatQ, to_lon: LonQ, to_lat: LatQ) -> dict:
    try:
        result = await routing.route(from_lon, from_lat, to_lon, to_lat)
    except routing.RoutingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (httpx.HTTPError, OSError, ImportError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Routing engine unavailable: {exc}") from exc
    result["straight_line_m"] = spatial.straight_line_m(from_lon, from_lat, to_lon, to_lat)
    return result


@router.get("/coverage", response_model=CoverageResponse,
            summary="Facility service-coverage analysis (EPSG:32643 buffers)")
def coverage(
    type: Annotated[FacilityType, Query(description="Facility class")],
    radius_m: Annotated[float, Query(ge=100, le=10_000)] = 1000,
    include_geometry: bool = True,
) -> dict:
    return spatial.coverage(type, radius_m, include_geometry)
