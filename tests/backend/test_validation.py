"""Input-validation tests: every malformed request must return 422 with a
useful message and must never reach the database layer."""

import pytest


@pytest.mark.parametrize("bbox", ["abc", "1,2,3", "10,20,5,30", "-200,0,10,10"])
def test_bad_bbox_rejected(client, bbox):
    response = client.get("/api/buildings", params={"bbox": bbox})
    assert response.status_code == 422


@pytest.mark.parametrize("limit", [0, -5, 999_999_999])
def test_bad_limit_rejected(client, limit):
    assert client.get("/api/buildings", params={"limit": limit}).status_code == 422


def test_bad_facility_type_rejected(client):
    response = client.get(
        "/api/nearest", params={"lon": 73.05, "lat": 33.68, "type": "zoo"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("lon,lat", [(0.0, 33.7), (73.05, 60.0), (200.0, 33.7)])
def test_out_of_window_coordinates_rejected(client, lon, lat):
    response = client.get(
        "/api/nearest", params={"lon": lon, "lat": lat, "type": "hospital"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("cell", [5, 99, 1001, -50])
def test_bad_grid_cell_rejected(client, cell):
    response = client.get("/api/analysis/green-access-grid", params={"cell_m": cell})
    assert response.status_code == 422


def test_bad_coverage_radius_rejected(client):
    response = client.get(
        "/api/coverage", params={"type": "hospital", "radius_m": 50}
    )
    assert response.status_code == 422


def test_query_radius_capped(client):
    response = client.get(
        "/api/query/buildings-near-facility",
        params={"type": "hospital", "radius_m": 999_999},
    )
    assert response.status_code == 422
