"""Spatial query tool endpoints (PostGIS-backed)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.models import FacilityType
from app.services import analysis

router = APIRouter(prefix="/api/query", tags=["Spatial Query"])

LonQ = Annotated[float, Query(ge=79.0, le=82.5)]
LatQ = Annotated[float, Query(ge=5.5, le=10.0)]
RadiusQ = Annotated[float, Query(ge=10, le=10_000, description="Radius in metres")]


@router.get("/buildings-near-facility",
            summary="Buildings within a radius of any facility of a type")
def buildings_near_facility(
    type: Annotated[FacilityType, Query()],
    radius_m: RadiusQ = 500,
    limit: Annotated[int, Query(ge=1, le=20_000)] = 5000,
) -> dict:
    return analysis.buildings_near_facility(type, radius_m, limit)


@router.get("/facilities-within",
            summary="Facilities within a radius of a point")
def facilities_within(
    lon: LonQ, lat: LatQ,
    radius_m: RadiusQ = 1000,
    type: Annotated[FacilityType | None, Query()] = None,
) -> dict:
    return analysis.facilities_within(lon, lat, radius_m, type)


@router.get("/facilities-near-roads",
            summary="Facilities of a type near major roads (motorway/trunk/primary/secondary)")
def facilities_near_roads(
    type: Annotated[FacilityType, Query()],
    radius_m: RadiusQ = 100,
) -> dict:
    return analysis.facilities_near_major_roads(type, radius_m)
