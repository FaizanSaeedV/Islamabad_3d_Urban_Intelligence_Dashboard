"""FastAPI application entry point.

Run locally:
    cd backend
    uvicorn app.main:app --reload --port 8000
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg_pool import PoolTimeout

from app import __version__
from app.core import db
from app.core.config import get_settings
from app.routers import analysis, analytics, layers, mobility, query, simulation, weather
from app.services import simulation as sim_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Open the DB pool and start the simulation loop for the app lifetime."""
    stop_event = asyncio.Event()
    sim_task: asyncio.Task | None = None
    try:
        db.open_pool()
        sim_task = asyncio.create_task(sim_engine.run_loop(stop_event))
    except Exception as exc:  # pragma: no cover - depends on local DB
        logger.warning("Startup degraded (database unavailable?): %s", exc)
    yield
    stop_event.set()
    if sim_task:
        await sim_task
    db.close_pool()


app = FastAPI(
    title="Smart City Digital Twin API",
    description=(
        "REST API for the Islamabad 3D Urban Intelligence Digital Twin. "
        "Serves OpenStreetMap-derived urban infrastructure from PostGIS, "
        "live weather from Open-Meteo, OSRM routing, spatial analysis, and a "
        "clearly-labelled digital twin simulation layer. "
        "Simulation data is 'Simulated for Digital Twin Demonstration' - "
        "never official real-time telemetry."
    ),
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Database unavailability -> clean 503 instead of a 500 stack trace
# ---------------------------------------------------------------------------
@app.exception_handler(PoolTimeout)
@app.exception_handler(psycopg.OperationalError)
async def db_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Database unavailable for %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable. Try again shortly."},
    )


@app.exception_handler(RuntimeError)
async def runtime_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    if "Connection pool is not open" in str(exc):
        return JSONResponse(status_code=503, content={"detail": "Database not connected."})
    raise exc


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(layers.router)
app.include_router(mobility.router)
app.include_router(analytics.router)
app.include_router(weather.router)
app.include_router(simulation.router)
app.include_router(analysis.router)
app.include_router(query.router)


@app.get("/", tags=["Health"])
def root() -> dict:
    """API landing endpoint."""
    return {
        "name": "Smart City Digital Twin API",
        "version": __version__,
        "study_area": "Islamabad, Pakistan",
        "docs": "/docs",
    }


@app.get("/api/health", tags=["Health"])
def health() -> dict:
    """Service and database health check."""
    database: dict
    try:
        database = db.check_database()
    except Exception as exc:
        database = {"connected": False, "error": str(exc)}
    return {"status": "ok", "version": __version__, "database": database}
