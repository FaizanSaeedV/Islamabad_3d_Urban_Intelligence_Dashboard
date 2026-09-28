"""API contract tests that run with or without a live database.

When PostGIS is up, data endpoints must return valid GeoJSON; when it is
down they must degrade to a clean 503 (never a 500 stack trace).
"""


def test_root(client):
    body = client.get("/").json()
    assert body["name"] == "Smart City Digital Twin API"
    assert body["study_area"] == "Islamabad, Pakistan"


def test_health_shape(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "database" in body and "connected" in body["database"]


def test_openapi_has_all_documented_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    required = [
        "/api/buildings", "/api/roads", "/api/facilities", "/api/hospitals",
        "/api/fuel-stations", "/api/ev-stations", "/api/parking",
        "/api/analytics", "/api/nearest", "/api/route", "/api/coverage",
        "/api/weather", "/api/simulation/status",
        "/api/analysis/green-space", "/api/analysis/green-access-grid",
        "/api/analysis/building-density",
        "/api/query/buildings-near-facility", "/api/query/facilities-within",
        "/api/query/facilities-near-roads",
    ]
    missing = [p for p in required if p not in paths]
    assert not missing, f"missing routes: {missing}"


def test_layer_endpoint_degrades_cleanly(client, db_ok):
    response = client.get("/api/buildings", params={"limit": 5})
    if db_ok:
        assert response.status_code == 200
        body = response.json()
        assert body["type"] == "FeatureCollection"
        assert len(body["features"]) <= 5
    else:
        assert response.status_code == 503
        assert "detail" in response.json()


def test_simulation_status_shape(client, db_ok):
    response = client.get("/api/simulation/status")
    if db_ok:
        body = response.json()
        assert body["is_simulated"] is True
        assert body["disclaimer"] == "Simulated for Digital Twin Demonstration"
        assert set(body) >= {"traffic", "parking", "ev_chargers"}
    else:
        assert response.status_code == 503
