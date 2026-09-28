"""GeoJSON layer endpoints: buildings, roads, facilities, and friends."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings
from app.schemas.models import FacilityType
from app.services import layers

router = APIRouter(prefix="/api", tags=["Layers"])

settings = get_settings()

BboxQ = Annotated[
    str | None,
    Query(
        description="Bounding box filter 'west,south,east,north' (EPSG:4326)",
        examples=["72.80,33.60,73.25,33.82"],
    ),
]
LimitQ = Annotated[int, Query(ge=1, le=200_000, description="Maximum features")]
SimplifyQ = Annotated[
    float | None,
    Query(ge=0, le=500, description="Geometry simplification tolerance in metres"),
]


def parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if bbox is None:
        return None
    try:
        west, south, east, north = (float(v) for v in bbox.split(","))
    except ValueError as exc:
        raise HTTPException(422, "bbox must be 'west,south,east,north'") from exc
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise HTTPException(422, "bbox out of range or west>=east / south>=north")
    return (west, south, east, north)


def _layer_endpoint(layer: str, bbox: str | None, limit: int, simplify_m: float | None) -> dict:
    return layers.get_layer(layer, bbox=parse_bbox(bbox), limit=limit, simplify_m=simplify_m)


@router.get("/buildings", summary="Building footprints (GeoJSON)")
def buildings(bbox: BboxQ = None, limit: LimitQ = 100_000, simplify_m: SimplifyQ = None) -> dict:
    return _layer_endpoint("buildings", bbox, limit, simplify_m)


@router.get("/roads", summary="Road network (GeoJSON)")
def roads(bbox: BboxQ = None, limit: LimitQ = 100_000, simplify_m: SimplifyQ = None) -> dict:
    return _layer_endpoint("roads", bbox, limit, simplify_m)


@router.get("/railways", summary="Railway lines (GeoJSON)")
def railways(bbox: BboxQ = None, limit: LimitQ = 10_000, simplify_m: SimplifyQ = None) -> dict:
    return _layer_endpoint("railways", bbox, limit, simplify_m)


@router.get("/waterways", summary="Rivers and canals (GeoJSON)")
def waterways(bbox: BboxQ = None, limit: LimitQ = 10_000, simplify_m: SimplifyQ = None) -> dict:
    return _layer_endpoint("waterways", bbox, limit, simplify_m)


@router.get("/water-bodies", summary="Water body polygons (GeoJSON)")
def water_bodies(bbox: BboxQ = None, limit: LimitQ = 10_000, simplify_m: SimplifyQ = None) -> dict:
    return _layer_endpoint("water_bodies", bbox, limit, simplify_m)


@router.get("/landuse", summary="Land-use polygons (GeoJSON)")
def landuse(bbox: BboxQ = None, limit: LimitQ = 50_000, simplify_m: SimplifyQ = None) -> dict:
    return _layer_endpoint("landuse", bbox, limit, simplify_m)


@router.get("/green-spaces", summary="Green spaces (GeoJSON)")
def green_spaces(bbox: BboxQ = None, limit: LimitQ = 20_000, simplify_m: SimplifyQ = None) -> dict:
    return _layer_endpoint("green_spaces", bbox, limit, simplify_m)


@router.get("/facilities", summary="Urban facilities (GeoJSON), optional type filter")
def facilities(
    type: Annotated[FacilityType | None, Query(description="Facility class")] = None,
    limit: LimitQ = 20_000,
) -> dict:
    return layers.get_facilities(type, limit)


# Convenience aliases (fixed type)
@router.get("/hospitals", summary="Hospitals & clinics (GeoJSON)")
def hospitals() -> dict:
    return layers.get_facilities("hospital")


@router.get("/fuel-stations", summary="Fuel stations (GeoJSON)")
def fuel_stations() -> dict:
    return layers.get_facilities("fuel_station")


@router.get("/ev-stations", summary="EV charging stations (GeoJSON)")
def ev_stations() -> dict:
    return layers.get_facilities("ev_charging")


@router.get("/parking", summary="Parking locations (GeoJSON)")
def parking() -> dict:
    return layers.get_facilities("parking")
