"""Download OpenStreetMap data for the Islamabad study area via the Overpass API.

Usage:
    python download_osm_data.py             # all themes
    python download_osm_data.py buildings roads   # selected themes

Each theme is saved as data/raw/<theme>.geojson (EPSG:4326).
Re-running overwrites files (idempotent). Between themes the script sleeps
briefly to respect the free Overpass servers' fair-use policy.

Data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import logging
import sys
import time

from osm_common import (
    BBOX_STR,
    RAW_DIR,
    elements_to_feature_collection,
    run_overpass_query,
    save_geojson,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("download")

PAUSE_BETWEEN_THEMES = 10  # seconds

# ---------------------------------------------------------------------------
# Theme definitions.
#   selector      - Overpass QL statements (without header/footer)
#   geometry_kind - point | line | polygon
#   out           - Overpass output mode ('geom' for full geometry,
#                   'center' for centroid points)
# ---------------------------------------------------------------------------
THEMES: dict[str, dict] = {
    "buildings": {
        "selector": f"""
            way["building"]({BBOX_STR});
            relation["building"]["type"="multipolygon"]({BBOX_STR});
        """,
        "geometry_kind": "polygon",
        "out": "geom",
    },
    "roads": {
        "selector": f"""way["highway"]({BBOX_STR});""",
        "geometry_kind": "line",
        "out": "geom",
    },
    "railways": {
        "selector": f"""way["railway"~"^(rail|light_rail|tram|subway)$"]({BBOX_STR});""",
        "geometry_kind": "line",
        "out": "geom",
    },
    "railway_stations": {
        "selector": f"""nwr["railway"="station"]({BBOX_STR});""",
        "geometry_kind": "point",
        "out": "center",
    },
    "water_bodies": {
        "selector": f"""
            way["natural"="water"]({BBOX_STR});
            relation["natural"="water"]({BBOX_STR});
            way["landuse"~"^(reservoir|basin)$"]({BBOX_STR});
        """,
        "geometry_kind": "polygon",
        "out": "geom",
    },
    "waterways": {
        "selector": f"""way["waterway"~"^(river|canal|stream)$"]({BBOX_STR});""",
        "geometry_kind": "line",
        "out": "geom",
    },
    "landuse": {
        "selector": f"""
            way["landuse"]({BBOX_STR});
            relation["landuse"]["type"="multipolygon"]({BBOX_STR});
        """,
        "geometry_kind": "polygon",
        "out": "geom",
    },
    "green_spaces": {
        "selector": f"""
            way["leisure"~"^(park|garden|playground|pitch|nature_reserve|recreation_ground)$"]({BBOX_STR});
            relation["leisure"~"^(park|garden|playground|pitch|nature_reserve|recreation_ground)$"]({BBOX_STR});
            way["landuse"~"^(grass|recreation_ground|forest|meadow|cemetery)$"]({BBOX_STR});
        """,
        "geometry_kind": "polygon",
        "out": "geom",
    },
    "hospitals": {
        "selector": f"""nwr["amenity"="hospital"]({BBOX_STR});""",
        "geometry_kind": "point",
        "out": "center",
    },
    "police_stations": {
        "selector": f"""nwr["amenity"="police"]({BBOX_STR});""",
        "geometry_kind": "point",
        "out": "center",
    },
    "fire_stations": {
        "selector": f"""nwr["amenity"="fire_station"]({BBOX_STR});""",
        "geometry_kind": "point",
        "out": "center",
    },
    "schools": {
        "selector": f"""nwr["amenity"~"^(school|college|university)$"]({BBOX_STR});""",
        "geometry_kind": "point",
        "out": "center",
    },
    "fuel_stations": {
        "selector": f"""nwr["amenity"="fuel"]({BBOX_STR});""",
        "geometry_kind": "point",
        "out": "center",
    },
    "ev_charging": {
        "selector": f"""nwr["amenity"="charging_station"]({BBOX_STR});""",
        "geometry_kind": "point",
        "out": "center",
    },
    "bus_stops": {
        "selector": f"""
            node["highway"="bus_stop"]({BBOX_STR});
            node["public_transport"="platform"]["bus"="yes"]({BBOX_STR});
        """,
        "geometry_kind": "point",
        "out": "center",
    },
    "parking": {
        "selector": f"""nwr["amenity"="parking"]({BBOX_STR});""",
        "geometry_kind": "point",
        "out": "center",
    },
}


def build_query(theme: dict) -> str:
    out_mode = "out center tags;" if theme["out"] == "center" else "out geom;"
    return f"[out:json][timeout:180];({theme['selector']});{out_mode}"


def download_theme(name: str) -> int:
    theme = THEMES[name]
    logger.info("=== Theme: %s ===", name)
    data = run_overpass_query(build_query(theme))
    collection = elements_to_feature_collection(data.get("elements", []), theme["geometry_kind"])
    save_geojson(collection, RAW_DIR / f"{name}.geojson")
    return len(collection["features"])


def main(argv: list[str]) -> None:
    force = "--force" in argv
    argv = [a for a in argv if a != "--force"]
    selected = argv or list(THEMES)
    unknown = [t for t in selected if t not in THEMES]
    if unknown:
        sys.exit(f"Unknown theme(s): {unknown}. Available: {', '.join(THEMES)}")

    summary: dict[str, int] = {}
    for i, name in enumerate(selected):
        # Resume support: skip themes already downloaded (use --force or
        # delete data/raw/<theme>.geojson to re-fetch).
        out_path = RAW_DIR / f"{name}.geojson"
        if out_path.exists() and not force:
            logger.info("=== Theme: %s === already downloaded, skipping (use --force to refresh)", name)
            continue
        summary[name] = download_theme(name)
        if i < len(selected) - 1:
            time.sleep(PAUSE_BETWEEN_THEMES)

    logger.info("--- Download summary ---")
    for name, count in summary.items():
        logger.info("%-18s %6d features", name, count)


if __name__ == "__main__":
    main(sys.argv[1:])
