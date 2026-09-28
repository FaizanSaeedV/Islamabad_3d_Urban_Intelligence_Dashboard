"""Digital twin simulation engine.

Generates and periodically updates DEMONSTRATION status values for traffic,
parking occupancy, and EV charger availability. Every value is stored with
is_simulated = TRUE and the fixed disclaimer 'Simulated for Digital Twin
Demonstration' (enforced by database CHECK constraints). This module never
produces data presented as real telemetry.

Update model: per-row Markov-style transition - with probability
TRANSITION_P a row steps one state up/down (traffic/parking) or resamples
(EV). This yields gradual, plausible-looking state evolution rather than
random flicker, while remaining an openly synthetic process.
"""

import asyncio
import logging
import random

from app.core import db

logger = logging.getLogger(__name__)

UPDATE_INTERVAL_S = 60
TRANSITION_P = 0.25

TRAFFIC_ORDER = ["low", "moderate", "high", "severe"]
SPEED_FACTOR = {"low": 1.0, "moderate": 0.7, "high": 0.45, "severe": 0.25}
PARKING_ORDER = ["available", "limited", "full"]
EV_STATES = ["available", "busy", "offline"]
EV_WEIGHTS = [0.6, 0.3, 0.1]


def _step(current: str, order: list[str], rng: random.Random) -> str:
    """Move one state up or down the ordered scale (bounded)."""
    i = order.index(current)
    i += rng.choice([-1, 1])
    return order[max(0, min(len(order) - 1, i))]


def tick(rng: random.Random | None = None) -> dict:
    """Advance the simulation one step. Returns counts of updated rows."""
    rng = rng or random.Random()
    updated = {"traffic": 0, "parking": 0, "ev": 0}

    for row in db.fetch_all("SELECT id, status FROM sim_traffic_status"):
        if rng.random() < TRANSITION_P:
            new_status = _step(row["status"], TRAFFIC_ORDER, rng)
            db.execute(
                """UPDATE sim_traffic_status
                   SET status = %(s)s, speed_factor = %(f)s, updated_at = now()
                   WHERE id = %(id)s""",
                {"s": new_status, "f": SPEED_FACTOR[new_status], "id": row["id"]},
            )
            updated["traffic"] += 1

    for row in db.fetch_all("SELECT id, occupancy_pct FROM sim_parking_status"):
        if rng.random() < TRANSITION_P:
            occ = float(row["occupancy_pct"]) + rng.uniform(-15, 15)
            occ = max(0.0, min(100.0, occ))
            status = "available" if occ < 60 else ("limited" if occ < 90 else "full")
            db.execute(
                """UPDATE sim_parking_status
                   SET status = %(s)s, occupancy_pct = %(o)s, updated_at = now()
                   WHERE id = %(id)s""",
                {"s": status, "o": round(occ, 1), "id": row["id"]},
            )
            updated["parking"] += 1

    for row in db.fetch_all("SELECT id FROM sim_ev_status"):
        if rng.random() < TRANSITION_P:
            db.execute(
                """UPDATE sim_ev_status
                   SET status = %(s)s, updated_at = now() WHERE id = %(id)s""",
                {"s": rng.choices(EV_STATES, EV_WEIGHTS)[0], "id": row["id"]},
            )
            updated["ev"] += 1
    return updated


def status() -> dict:
    """Current simulation state for all three layers."""
    traffic = db.fetch_all(
        """SELECT road_id, status, speed_factor, updated_at
           FROM sim_traffic_status ORDER BY road_id"""
    )
    parking = db.fetch_all(
        """SELECT s.facility_id, f.name, ST_X(f.geom) AS lon, ST_Y(f.geom) AS lat,
                  s.status, s.occupancy_pct, s.updated_at
           FROM sim_parking_status s JOIN facilities f ON f.id = s.facility_id
           ORDER BY s.facility_id"""
    )
    ev = db.fetch_all(
        """SELECT s.facility_id, f.name, ST_X(f.geom) AS lon, ST_Y(f.geom) AS lat,
                  s.status, s.updated_at
           FROM sim_ev_status s JOIN facilities f ON f.id = s.facility_id
           ORDER BY s.facility_id"""
    )
    return {"traffic": traffic, "parking": parking, "ev_chargers": ev}


async def run_loop(stop_event: asyncio.Event) -> None:
    """Background task: advance the simulation every UPDATE_INTERVAL_S seconds."""
    logger.info("Simulation engine loop started (interval %ss).", UPDATE_INTERVAL_S)
    while not stop_event.is_set():
        try:
            counts = await asyncio.to_thread(tick)
            logger.debug("Simulation tick: %s", counts)
        except Exception as exc:  # DB down etc. - keep looping, try again later
            logger.warning("Simulation tick skipped: %s", exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=UPDATE_INTERVAL_S)
        except asyncio.TimeoutError:
            pass
    logger.info("Simulation engine loop stopped.")
