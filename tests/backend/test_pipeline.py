"""Data-pipeline tests using the clearly-labelled synthetic fixture.

Validates geometry repair, deduplication, bbox filtering, and all three
height-estimation paths of scripts/process_data.py.
"""

import shutil

import pytest


@pytest.fixture()
def pipeline_dirs(tmp_path, fixture_buildings_path, monkeypatch):
    """Point the pipeline modules at temporary raw/processed directories."""
    import process_data

    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    shutil.copy(fixture_buildings_path, raw / "buildings.geojson")
    monkeypatch.setattr(process_data, "RAW_DIR", raw)
    monkeypatch.setattr(process_data, "PROCESSED_DIR", processed)
    return process_data, processed


def test_process_buildings_fixture(pipeline_dirs):
    process_data, processed = pipeline_dirs
    stats = process_data.process_theme("buildings")

    assert stats["input"] == 6
    assert stats["output"] == 4
    assert stats["repaired"] == 1          # self-intersecting bowtie
    assert stats["dropped_duplicate"] == 1
    assert stats["dropped_outside"] == 1   # feature outside Islamabad bbox

    from osm_common import load_geojson
    result = load_geojson(processed / "buildings.geojson")
    by_id = {f["properties"]["osm_id"]: f["properties"] for f in result["features"]}

    # Height rule 2: levels x 3.0 m
    assert by_id[1001]["height_m"] == 12.0
    assert by_id[1001]["height_source"] == "levels_x3"
    # Height rule 1: parseable OSM height tag ("27.5 m")
    assert by_id[1002]["height_m"] == 27.5
    assert by_id[1002]["height_source"] == "osm_height"
    # Height rule 3: default fallback, honestly flagged
    assert by_id[1003]["height_m"] == 6.0
    assert by_id[1003]["height_source"] == "default_assumed"
    # 12 levels -> 36 m
    assert by_id[1005]["height_m"] == 36.0

    # Metric area computed in EPSG:32643: fixture squares are ~0.001 deg
    # around 33.7 N (~93 m x 111 m).
    assert 9_500 < by_id[1001]["footprint_area_m2"] < 11_500


def test_height_parser_edge_cases():
    from process_data import estimate_building_height

    assert estimate_building_height({"height": "27.5 m"})[2] == "osm_height"
    assert estimate_building_height({"height": "1"})[2] == "default_assumed"   # <2 m implausible
    assert estimate_building_height({"height": "999"})[2] == "default_assumed" # >400 m implausible
    assert estimate_building_height({"building:levels": "4"}) == (12.0, 4, "levels_x3")
    assert estimate_building_height({}) == (6.0, None, "default_assumed")
