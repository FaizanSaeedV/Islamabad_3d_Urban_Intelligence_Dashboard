"""Validate and clean raw OSM GeoJSON into analysis-ready processed files.

Steps per theme:
  1. Geometry validation and repair (shapely make_valid); empty/irreparable dropped.
  2. Duplicate removal (same osm_type/osm_id).
  3. Study-area filter (feature must intersect the Islamabad bbox).
  4. Attribute normalisation to a compact, documented schema.
  5. Building-height estimation (documented rule, see HEIGHT_RULE below).
  6. Metric length/area computed in EPSG:32643 (WGS 84 / UTM zone 43N)
     - never in geographic coordinates.
  7. Processing report written to data/processed/processing_report.json.

Usage:
    python process_data.py            # all themes found in data/raw/
    python process_data.py buildings  # selected themes
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import box, mapping, shape
from shapely.ops import transform as shp_transform
from shapely.validation import make_valid

from osm_common import BBOX, PROCESSED_DIR, RAW_DIR, load_geojson, save_geojson

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("process")

# WGS84 -> WGS 84 / UTM zone 43N (metric CRS for Islamabad)
TO_METRIC = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True).transform
STUDY_AREA = box(BBOX[1], BBOX[0], BBOX[3], BBOX[2])  # (west, south, east, north)

# ---------------------------------------------------------------------------
# HEIGHT_RULE (documented in docs/GIS_METHODOLOGY.md):
#   1. OSM `height` tag (metres) when parseable  -> height_source = "osm_height"
#   2. else `building:levels` x 3.0 m/level      -> height_source = "levels_x3"
#   3. else default 6.0 m (assumed 2 levels)     -> height_source = "default_assumed"
# 3.0 m/level is a standard assumption for mixed low-rise stock; defaults are
# clearly flagged so no fabricated height is presented as measured data.
# ---------------------------------------------------------------------------
METRES_PER_LEVEL = 3.0
DEFAULT_HEIGHT_M = 6.0
DEFAULT_LEVELS = 2

_NUM = re.compile(r"[-+]?\d*\.?\d+")


def _parse_number(value) -> float | None:
    if value is None:
        return None
    match = _NUM.search(str(value).replace(",", "."))
    return float(match.group()) if match else None


def estimate_building_height(tags: dict) -> tuple[float, int | None, str]:
    height = _parse_number(tags.get("height"))
    levels = _parse_number(tags.get("building:levels"))
    levels_int = int(levels) if levels and levels > 0 else None
    if height and 2.0 <= height <= 400.0:
        return round(height, 1), levels_int, "osm_height"
    if levels_int:
        return round(levels_int * METRES_PER_LEVEL, 1), levels_int, "levels_x3"
    return DEFAULT_HEIGHT_M, None, "default_assumed"


# ---------------------------------------------------------------------------
# Attribute normalisation per theme
# ---------------------------------------------------------------------------
def _common(props: dict) -> dict:
    return {
        "osm_type": props.get("osm_type"),
        "osm_id": props.get("osm_id"),
        "name": props.get("name") or props.get("name:en"),
    }


def norm_buildings(props: dict, geom_metric) -> dict:
    height_m, levels, source = estimate_building_height(props)
    return {
        **_common(props),
        "building_type": props.get("building") if props.get("building") != "yes" else "unspecified",
        "levels": levels,
        "height_m": height_m,
        "height_source": source,
        "amenity": props.get("amenity"),
        "footprint_area_m2": round(geom_metric.area, 1),
    }


def norm_roads(props: dict, geom_metric) -> dict:
    return {
        **_common(props),
        "highway": props.get("highway"),
        "oneway": props.get("oneway") == "yes",
        "lanes": _parse_number(props.get("lanes")),
        "surface": props.get("surface"),
        "maxspeed": _parse_number(props.get("maxspeed")),
        "length_m": round(geom_metric.length, 1),
    }


def norm_railways(props: dict, geom_metric) -> dict:
    return {
        **_common(props),
        "railway": props.get("railway"),
        "gauge": props.get("gauge"),
        "length_m": round(geom_metric.length, 1),
    }


def norm_polygons(props: dict, geom_metric) -> dict:
    return {
        **_common(props),
        "landuse": props.get("landuse"),
        "leisure": props.get("leisure"),
        "natural": props.get("natural"),
        "area_m2": round(geom_metric.area, 1),
    }


def norm_facility(props: dict, geom_metric) -> dict:  # noqa: ARG001 - points have no area
    return {
        **_common(props),
        "amenity": props.get("amenity"),
        "railway": props.get("railway"),
        "highway": props.get("highway"),
        "operator": props.get("operator"),
        "opening_hours": props.get("opening_hours"),
        "capacity": _parse_number(props.get("capacity")),
        "emergency": props.get("emergency"),
        "beds": _parse_number(props.get("beds")),
    }


def norm_waterways(props: dict, geom_metric) -> dict:
    return {**_common(props), "waterway": props.get("waterway"), "length_m": round(geom_metric.length, 1)}


NORMALISERS = {
    "buildings": norm_buildings,
    "roads": norm_roads,
    "railways": norm_railways,
    "waterways": norm_waterways,
    "water_bodies": norm_polygons,
    "landuse": norm_polygons,
    "green_spaces": norm_polygons,
}

FACILITY_THEMES = {
    "hospitals", "police_stations", "fire_stations", "schools", "fuel_stations",
    "ev_charging", "bus_stops", "parking", "railway_stations",
}


def normalise(theme: str, props: dict, geom_metric) -> dict:
    if theme in FACILITY_THEMES:
        return norm_facility(props, geom_metric)
    fn = NORMALISERS.get(theme)
    return fn(props, geom_metric) if fn else _common(props)


# ---------------------------------------------------------------------------
def process_theme(theme: str) -> dict:
    raw_path = RAW_DIR / f"{theme}.geojson"
    if not raw_path.exists():
        logger.warning("Skipping %s: %s not found (run download_osm_data.py first)", theme, raw_path.name)
        return {"theme": theme, "status": "missing_raw"}

    raw = load_geojson(raw_path)
    stats = {
        "theme": theme, "status": "ok", "input": len(raw["features"]),
        "repaired": 0, "dropped_invalid": 0, "dropped_duplicate": 0,
        "dropped_outside": 0, "output": 0,
    }
    seen: set[tuple] = set()
    features_out = []

    for feature in raw["features"]:
        props = feature.get("properties", {})
        key = (props.get("osm_type"), props.get("osm_id"))
        if key in seen:
            stats["dropped_duplicate"] += 1
            continue
        seen.add(key)

        try:
            geom = shape(feature["geometry"])
        except Exception:  # noqa: BLE001
            stats["dropped_invalid"] += 1
            continue
        if not geom.is_valid:
            geom = make_valid(geom)
            stats["repaired"] += 1
        if geom.is_empty:
            stats["dropped_invalid"] += 1
            continue
        if not geom.intersects(STUDY_AREA):
            stats["dropped_outside"] += 1
            continue

        geom_metric = shp_transform(TO_METRIC, geom)
        new_props = {k: v for k, v in normalise(theme, props, geom_metric).items() if v is not None}
        features_out.append({
            "type": "Feature",
            "id": feature.get("id"),
            "geometry": mapping(geom),
            "properties": new_props,
        })

    stats["output"] = len(features_out)
    save_geojson(
        {
            "type": "FeatureCollection",
            "features": features_out,
            "metadata": {
                **raw.get("metadata", {}),
                "processed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "metric_crs": "EPSG:32643 (WGS 84 / UTM zone 43N) for length/area attributes",
            },
        },
        PROCESSED_DIR / f"{theme}.geojson",
    )
    logger.info("%s: %d in -> %d out (repaired %d, dup %d, invalid %d, outside %d)",
                theme, stats["input"], stats["output"], stats["repaired"],
                stats["dropped_duplicate"], stats["dropped_invalid"], stats["dropped_outside"])
    return stats


def main(argv: list[str]) -> None:
    all_themes = sorted(p.stem for p in RAW_DIR.glob("*.geojson"))
    selected = argv or all_themes
    if not selected:
        sys.exit("No raw data found. Run download_osm_data.py first.")

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "themes": [process_theme(t) for t in selected],
    }
    report_path = PROCESSED_DIR / "processing_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    logger.info("Report written to %s", report_path)


if __name__ == "__main__":
    main(sys.argv[1:])
