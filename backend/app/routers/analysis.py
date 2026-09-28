"""Advanced GIS analysis endpoints: accessibility & density grids,
green-space statistics."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.services import analysis

router = APIRouter(prefix="/api/analysis", tags=["Advanced GIS Analysis"])

LonQ = Annotated[float, Query(ge=79.0, le=82.5, description="Longitude (EPSG:4326)")]
LatQ = Annotated[float, Query(ge=5.5, le=10.0, description="Latitude (EPSG:4326)")]
CellQ = Annotated[float, Query(ge=100, le=1000, description="Grid cell size in metres (EPSG:32643)")]


@router.get("/green-space", summary="Green-space accessibility from a point")
def green_space(lon: LonQ, lat: LatQ,
                radius_m: Annotated[float, Query(ge=100, le=10_000)] = 1000) -> dict:
    return analysis.green_space_point_stats(lon, lat, radius_m)


@router.get("/green-access-grid",
            summary="Green-space accessibility grid (GeoJSON choropleth)")
def green_access_grid(cell_m: CellQ = 250) -> dict:
    return analysis.green_access_grid(cell_m)


@router.get("/building-density",
            summary="Building density & mean height grid (GeoJSON choropleth)")
def building_density(cell_m: CellQ = 250) -> dict:
    return analysis.building_density_grid(cell_m)
