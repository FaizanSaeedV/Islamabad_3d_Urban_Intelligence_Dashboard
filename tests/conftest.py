"""Shared pytest fixtures.

- Adds backend/ and scripts/ to sys.path so tests import the app directly.
- `client`: FastAPI TestClient with lifespan (pool + simulation loop).
- `db_ok`: session-scoped database availability flag; DB-dependent spatial
  tests skip cleanly when PostGIS is not running.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def db_ok(client) -> bool:
    """True when a live PostGIS database answers the health check."""
    response = client.get("/api/health")
    return bool(response.json().get("database", {}).get("connected"))


@pytest.fixture()
def fixture_buildings_path() -> Path:
    return ROOT / "tests" / "fixtures" / "synthetic_buildings_fixture.geojson"
