"""Spatial-result validation against a LIVE PostGIS database.

These tests skip cleanly when the database is not loaded (CI/sandbox);
run them locally after Milestone 3 to validate real spatial output.
"""

import pytest


@pytest.fixture(autouse=True)
def _require_db(db_ok):
    if not db_ok:
        pytest.skip("PostGIS not available - run after database setup (M3)")


def test_all_geometries_are_wgs84(client):
    """Every coordinate served must lie inside the Islamabad study window."""
    body = client.get("/api/buildings", params={"limit": 200}).json()
    assert body["type"] == "FeatureCollection"
    for feature in body["features"]:
        geom = feature["geometry"]
        rings = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in rings:
            for ring in poly:
                for lon, lat in ring:
                    assert 72.75 < lon < 73.30, f"lon {lon} outside study window"
                    assert 33.55 < lat < 33.87, f"lat {lat} outside study window"


def test_nearest_results_sorted_and_metric(client):
    body = client.get(
        "/api/nearest",
        params={"lon": 73.0479, "lat": 33.6844, "type": "hospital", "n": 5},
    ).json()
    distances = [r["distance_m"] for r in body["results"]]
    assert distances == sorted(distances), "results must be distance-ordered"
    # sanity: nearest hospital to central Islamabad must be within 5 km
    if distances:
        assert distances[0] < 5000


def test_coverage_percentages_consistent(client):
    body = client.get(
        "/api/coverage",
        params={"type": "hospital", "radius_m": 1000, "include_geometry": False},
    ).json()
    assert body["covered_buildings"] + body["underserved_buildings"] == body["total_buildings"]
    assert 0.0 <= body["underserved_pct"] <= 100.0
    # larger radius must never cover fewer buildings
    wider = client.get(
        "/api/coverage",
        params={"type": "hospital", "radius_m": 2000, "include_geometry": False},
    ).json()
    assert wider["covered_buildings"] >= body["covered_buildings"]


def test_building_heights_within_constraints(client):
    body = client.get("/api/buildings", params={"limit": 500}).json()
    for feature in body["features"]:
        height = feature["properties"]["height_m"]
        assert 0 < height <= 500
        assert feature["properties"]["height_source"] in (
            "osm_height", "levels_x3", "default_assumed",
        )


def test_analytics_totals_consistent(client):
    body = client.get("/api/analytics").json()
    totals = body["totals"]
    assert totals["total_buildings"] >= 0
    height_sum = sum(body["building_height_classes"]["values"])
    assert height_sum == totals["total_buildings"], (
        "height classes must partition all buildings"
    )


def test_green_access_grid_valid(client):
    body = client.get("/api/analysis/green-access-grid", params={"cell_m": 500}).json()
    assert body["type"] == "FeatureCollection"
    assert body["metadata"]["crs_analysis"] == "EPSG:32643"
    for feature in body["features"][:100]:
        d = feature["properties"]["distance_m"]
        assert d is None or d >= 0
