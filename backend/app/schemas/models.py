"""Pydantic response models for non-GeoJSON endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

FacilityType = Literal[
    "hospital", "police_station", "fire_station", "school",
    "fuel_station", "ev_charging", "bus_stop", "parking", "railway_station",
]

SIM_DISCLAIMER = "Simulated for Digital Twin Demonstration"


class NearestFacility(BaseModel):
    id: int
    name: str | None
    facility_type: str
    lon: float
    lat: float
    distance_m: float


class NearestResponse(BaseModel):
    origin: dict
    facility_type: str
    method: str = (
        "KNN index pre-selection, exact geodesic (WGS 84 geography) re-ranking"
    )
    results: list[NearestFacility]


class RouteResponse(BaseModel):
    distance_m: float
    duration_s: float
    duration_note: str = (
        "OSRM demo-server estimate on the OSM road network; free-flow speeds, "
        "no live traffic."
    )
    straight_line_m: float
    geometry: dict  # GeoJSON LineString
    engine: str = "OSRM (public demo server)"


class CoverageResponse(BaseModel):
    facility_type: str
    radius_m: float
    facility_count: int
    total_buildings: int
    covered_buildings: int
    underserved_buildings: int
    underserved_pct: float
    method: str = (
        "Buffers generated and dissolved in EPSG:32643 (UTM zone 43N), tested against "
        "building centroids in the same CRS."
    )
    service_area: dict | None = None  # simplified GeoJSON MultiPolygon (EPSG:4326)


class WeatherResponse(BaseModel):
    location: str = "Islamabad, Pakistan"
    latitude: float
    longitude: float
    temperature_c: float | None = None
    humidity_pct: float | None = None
    precipitation_mm: float | None = None
    rain_mm: float | None = None
    cloud_cover_pct: float | None = None
    wind_speed_kmh: float | None = None
    wind_direction_deg: float | None = None
    weather_code: int | None = None
    is_day: bool | None = None
    fetched_at: datetime
    source: str = "Open-Meteo (CC BY 4.0, no API key)"


class SimTrafficItem(BaseModel):
    road_id: int
    status: Literal["low", "moderate", "high", "severe"]
    speed_factor: float
    updated_at: datetime


class SimParkingItem(BaseModel):
    facility_id: int
    name: str | None
    lon: float
    lat: float
    status: Literal["available", "limited", "full"]
    occupancy_pct: float
    updated_at: datetime


class SimEvItem(BaseModel):
    facility_id: int
    name: str | None
    lon: float
    lat: float
    status: Literal["available", "busy", "offline"]
    updated_at: datetime


class SimulationStatus(BaseModel):
    disclaimer: str = SIM_DISCLAIMER
    is_simulated: bool = True
    traffic: list[SimTrafficItem]
    parking: list[SimParkingItem]
    ev_chargers: list[SimEvItem]


class ChartData(BaseModel):
    labels: list[str]
    values: list[float]


class AnalyticsResponse(BaseModel):
    generated_at: datetime
    totals: dict[str, float]
    building_height_classes: ChartData
    building_types: ChartData
    facility_distribution: ChartData
    landuse_distribution: ChartData
    mobility_infrastructure: ChartData
    height_classification_note: str = (
        "Low-rise < 12 m, mid-rise 12-30 m, high-rise > 30 m (see "
        "docs/GIS_METHODOLOGY.md; heights partly estimated from building:levels)."
    )
