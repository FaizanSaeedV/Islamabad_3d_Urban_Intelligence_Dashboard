"""Shared utilities for the OSM data pipeline.

- Study-area definition (Islamabad, Pakistan)
- Overpass API client with mirror fallback and retry
- Overpass JSON -> GeoJSON conversion (nodes, ways, multipolygon relations)

Data source: OpenStreetMap (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests
from shapely.geometry import LineString, Point, Polygon, mapping
from shapely.ops import polygonize, unary_union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Study area: Islamabad urban area and immediate peri-urban surroundings
# Overpass bbox order: (south, west, north, east)
# ---------------------------------------------------------------------------
BBOX = (33.60, 72.80, 33.82, 73.25)
BBOX_STR = f"{BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]}"

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    # private.coffee before kumi: kumi.systems frequently hangs to the read
    # timeout under load, costing 5 min per attempt
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    # overpass.osm.jp removed: broken SSL certificate (hostname mismatch)
]

REQUEST_TIMEOUT = 300  # seconds; buildings query in a dense city is slow
RETRY_WAIT = 30        # seconds between retries (polite to free servers)
MAX_RETRIES = 6        # rotates across the mirror endpoints; resilient to
                       # flaky networks and 429 (server busy) responses

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


def run_overpass_query(query: str) -> dict:
    """Execute an Overpass QL query, rotating through mirror endpoints."""
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        endpoint = OVERPASS_ENDPOINTS[attempt % len(OVERPASS_ENDPOINTS)]
        try:
            logger.info("Overpass request -> %s (attempt %d)", endpoint, attempt + 1)
            response = requests.post(
                endpoint,
                data={"data": query},
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": "smart-city-digital-twin/1.0 (academic portfolio project)"},
            )
            if response.status_code == 429 or response.status_code == 504:
                raise requests.HTTPError(f"HTTP {response.status_code} (server busy)")
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - retry any transport error
            last_error = exc
            logger.warning("Overpass attempt %d failed: %s", attempt + 1, exc)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_WAIT)
    raise RuntimeError(f"Overpass query failed after {MAX_RETRIES} attempts: {last_error}")


# ---------------------------------------------------------------------------
# Overpass JSON -> GeoJSON
# ---------------------------------------------------------------------------
def _way_coords(element: dict) -> list[list[float]]:
    """Extract [lon, lat] coordinate list from a way returned with `out geom`."""
    return [[pt["lon"], pt["lat"]] for pt in element.get("geometry", [])]


def _is_closed(coords: list[list[float]]) -> bool:
    return len(coords) >= 4 and coords[0] == coords[-1]


def _relation_to_multipolygon(element: dict):
    """Assemble a (Multi)Polygon from a multipolygon relation with member geometry.

    Outer/inner rings may arrive split into several ways; shapely's
    polygonize handles ring stitching. Inner rings are subtracted.
    """
    outer_lines, inner_lines = [], []
    for member in element.get("members", []):
        if member.get("type") != "way" or "geometry" not in member:
            continue
        coords = [[pt["lon"], pt["lat"]] for pt in member["geometry"]]
        if len(coords) < 2:
            continue
        line = LineString(coords)
        if member.get("role") == "inner":
            inner_lines.append(line)
        else:  # 'outer' or missing role (treated as outer, per OSM convention)
            outer_lines.append(line)

    outers = list(polygonize(unary_union(outer_lines))) if outer_lines else []
    if not outers:
        return None
    geometry = unary_union(outers)
    if inner_lines:
        inners = list(polygonize(unary_union(inner_lines)))
        if inners:
            geometry = geometry.difference(unary_union(inners))
    return None if geometry.is_empty else geometry


def element_to_feature(element: dict, geometry_kind: str) -> dict | None:
    """Convert one Overpass element to a GeoJSON feature.

    geometry_kind:
        'point'   - node coordinates, or way/relation centroid (`out center`)
        'line'    - way as LineString
        'polygon' - closed way as Polygon / relation as MultiPolygon
    """
    etype, eid = element["type"], element["id"]
    tags = element.get("tags", {})
    geom = None

    if geometry_kind == "point":
        if etype == "node" and "lat" in element:
            geom = Point(element["lon"], element["lat"])
        elif "center" in element:
            geom = Point(element["center"]["lon"], element["center"]["lat"])

    elif geometry_kind == "line" and etype == "way":
        coords = _way_coords(element)
        if len(coords) >= 2:
            geom = LineString(coords)

    elif geometry_kind == "polygon":
        if etype == "way":
            coords = _way_coords(element)
            if _is_closed(coords):
                geom = Polygon(coords)
        elif etype == "relation":
            geom = _relation_to_multipolygon(element)

    if geom is None or geom.is_empty:
        return None

    return {
        "type": "Feature",
        "id": f"{etype}/{eid}",
        "geometry": mapping(geom),
        "properties": {"osm_type": etype, "osm_id": eid, **tags},
    }


def elements_to_feature_collection(elements: list[dict], geometry_kind: str) -> dict:
    features = []
    for el in elements:
        try:
            feature = element_to_feature(el, geometry_kind)
        except Exception as exc:  # noqa: BLE001 - skip malformed elements, keep pipeline running
            logger.warning("Skipping %s/%s: %s", el.get("type"), el.get("id"), exc)
            feature = None
        if feature:
            features.append(feature)
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "source": "OpenStreetMap via Overpass API",
            "license": "ODbL 1.0 (c) OpenStreetMap contributors",
            "bbox_swne": list(BBOX),
            "crs": "EPSG:4326",
        },
    }


def save_geojson(collection: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(collection, fh, ensure_ascii=False)
    logger.info("Wrote %s (%d features)", path.name, len(collection["features"]))


def load_geojson(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
