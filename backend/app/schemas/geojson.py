"""GeoJSON response models (RFC 7946)."""

from typing import Any, Literal

from pydantic import BaseModel


class Geometry(BaseModel):
    type: Literal[
        "Point", "MultiPoint", "LineString", "MultiLineString",
        "Polygon", "MultiPolygon", "GeometryCollection",
    ]
    coordinates: Any = None


class Feature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: int | str | None = None
    geometry: Geometry | None
    properties: dict[str, Any] = {}


class FeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[Feature]
    metadata: dict[str, Any] | None = None
