"""PostgreSQL/PostGIS connection pool management (psycopg 3)."""

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None


def open_pool() -> None:
    """Open the global connection pool. Called on application startup."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = ConnectionPool(
            conninfo=settings.database_dsn,
            min_size=1,
            max_size=10,
            timeout=5,  # fail fast instead of hanging when the DB is down
            open=True,
            kwargs={"row_factory": dict_row},
        )
        logger.info("Database connection pool opened.")


def close_pool() -> None:
    """Close the global connection pool. Called on application shutdown."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
        logger.info("Database connection pool closed.")


@contextmanager
def get_connection() -> Iterator[Any]:
    """Yield a pooled database connection."""
    if _pool is None:
        raise RuntimeError("Connection pool is not open. Call open_pool() first.")
    with _pool.connection() as conn:
        yield conn


def fetch_all(query: str, params: tuple | dict | None = None) -> list[dict]:
    """Run a read query and return all rows as dictionaries."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


def fetch_one(query: str, params: tuple | dict | None = None) -> dict | None:
    """Run a read query and return the first row (or None)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()


def execute(query: str, params: tuple | dict | None = None) -> None:
    """Run a write query (INSERT/UPDATE/DELETE)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()


def check_database() -> dict:
    """Health check: verify PostGIS is reachable and report its version."""
    row = fetch_one("SELECT PostGIS_Version() AS postgis_version")
    return {"connected": True, "postgis_version": row["postgis_version"] if row else None}
