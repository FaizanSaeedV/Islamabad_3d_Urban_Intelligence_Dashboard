"""Extract Islamabad application layers from a Pakistan OSM PBF file.

This is the offline fallback for periods when public Overpass endpoints are
busy. It reads only the Islamabad bounding box with GDAL/pyogrio and writes
the same raw GeoJSON theme files consumed by ``process_data.py``.

Usage:
    python scripts/extract_pbf_data.py data/pakistan.osm.pbf
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio
from shapely.geometry import mapping

from osm_common import BBOX, RAW_DIR, save_geojson

TAGS_RE = re.compile(r'"([^"\\]+)"=>"((?:\\.|[^"\\])*)"')
BBOX_XY = (BBOX[1], BBOX[0], BBOX[3], BBOX[2])


def parse_other_tags(value) -> dict:
    if not isinstance(value, str):
        return {}
    return {key: val.replace(r'\"', '"') for key, val in TAGS_RE.findall(value)}


def read_layer(pbf: Path, layer: str) -> gpd.GeoDataFrame:
    frame = pyogrio.read_dataframe(pbf, layer=layer, bbox=BBOX_XY)
    if "other_tags" in frame:
        expanded = pd.DataFrame(frame["other_tags"].map(parse_other_tags).tolist(), index=frame.index)
        for column in expanded:
            if column not in frame:
                frame[column] = expanded[column]
            else:
                frame[column] = frame[column].fillna(expanded[column])
    return frame


def features(frame: gpd.GeoDataFrame, osm_type: str, *, centroid: bool = False) -> list[dict]:
    output = []
    for _, row in frame.iterrows():
        geom = row.geometry.centroid if centroid else row.geometry
        props = {
            key: value.item() if hasattr(value, "item") else value
            for key, value in row.drop(labels="geometry").items()
            if value is not None and not (isinstance(value, float) and pd.isna(value))
        }
        props["osm_type"] = osm_type
        props["osm_id"] = str(props.get("osm_id") or props.get("osm_way_id"))
        output.append({
            "type": "Feature",
            "id": f"{osm_type}/{props['osm_id']}",
            "properties": props,
            "geometry": mapping(geom),
        })
    return output


def write_theme(name: str, rows: list[dict], source: Path) -> None:
    save_geojson({
        "type": "FeatureCollection",
        "features": rows,
        "metadata": {
            "source": f"OpenStreetMap via BBBike PBF: {source.name}",
            "license": "ODbL 1.0",
            "study_area_bbox": list(BBOX),
        },
    }, RAW_DIR / f"{name}.geojson")
    print(f"{name:18s} {len(rows):7d}")


def main(pbf_path: str) -> None:
    source = Path(pbf_path)
    if not source.exists():
        raise SystemExit(f"PBF not found: {source}")

    points = read_layer(source, "points")
    lines = read_layer(source, "lines")
    polygons = read_layer(source, "multipolygons")

    write_theme("buildings", features(polygons[polygons["building"].notna()], "way"), source)
    write_theme("roads", features(lines[lines["highway"].notna()], "way"), source)
    write_theme("railways", features(lines[lines["railway"].notna()], "way"), source)
    write_theme("waterways", features(lines[lines["waterway"].notna()], "way"), source)

    water = polygons[(polygons["natural"] == "water") | polygons["water"].notna()]
    write_theme("water_bodies", features(water, "way"), source)
    write_theme("landuse", features(polygons[polygons["landuse"].notna()], "way"), source)

    green = polygons[
        polygons["leisure"].isin(["park", "garden", "nature_reserve", "recreation_ground"])
        | polygons["landuse"].isin(["forest", "grass", "recreation_ground", "village_green"])
        | polygons["natural"].isin(["wood", "scrub"])
    ]
    write_theme("green_spaces", features(green, "way"), source)

    facility_filters = {
        "hospitals": points["amenity"].isin(["hospital", "clinic"]),
        "police_stations": points["amenity"].eq("police"),
        "fire_stations": points["amenity"].eq("fire_station"),
        "schools": points["amenity"].isin(["school", "college", "university"]),
        "fuel_stations": points["amenity"].eq("fuel"),
        "ev_charging": points["amenity"].eq("charging_station"),
        "bus_stops": points["highway"].eq("bus_stop") | points["public_transport"].eq("platform"),
        "parking": points["amenity"].eq("parking"),
        "railway_stations": points["railway"].isin(["station", "halt"]),
    }
    polygon_amenities = polygons[polygons["amenity"].notna()]
    for name, mask in facility_filters.items():
        point_rows = features(points[mask], "node")
        if name == "hospitals":
            extra = polygon_amenities[polygon_amenities["amenity"].isin(["hospital", "clinic"])]
        elif name == "schools":
            extra = polygon_amenities[polygon_amenities["amenity"].isin(["school", "college", "university"])]
        else:
            amenity = {
                "police_stations": "police", "fire_stations": "fire_station",
                "fuel_stations": "fuel", "ev_charging": "charging_station",
                "parking": "parking",
            }.get(name)
            extra = polygon_amenities[polygon_amenities["amenity"].eq(amenity)] if amenity else polygons.iloc[0:0]
        write_theme(name, point_rows + features(extra, "way", centroid=True), source)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/extract_pbf_data.py data/pakistan.osm.pbf")
    main(sys.argv[1])
