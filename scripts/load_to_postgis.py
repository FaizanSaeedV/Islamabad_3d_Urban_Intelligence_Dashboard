"""Load processed GeoJSON into the PostGIS database and seed simulation tables.

Prerequisites:
  1. PostgreSQL running, database created and schema applied:
       psql -U postgres -f database/schema/00_create_database.sql
       psql -U postgres -d smart_city_twin -f database/schema/01_extensions.sql
       psql -U postgres -d smart_city_twin -f database/schema/02_tables.sql
       psql -U postgres -d smart_city_twin -f database/schema/03_views.sql
       psql -U postgres -d smart_city_twin -f database/schema/04_simulation.sql
       psql -U postgres -d smart_city_twin -f database/schema/05_indexes.sql
     (or: python load_to_postgis.py --apply-schema  to run 01-05 automatically)
  2. scripts/download_osm_data.py and scripts/process_data.py have been run.
  3. Connection settings in .env at the repository root (see .env.example).

Usage:
    python load_to_postgis.py                 # load all available themes + seed simulation
    python load_to_postgis.py buildings roads # selected themes only
    python load_to_postgis.py --apply-schema  # apply schema SQL first, then load

The loader is idempotent: each theme is truncated and reloaded, then the
simulation tables are reseeded (they reference roads/facilities by FK).
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
import os

from osm_common import PROCESSED_DIR, ROOT, load_geojson

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("load")

load_dotenv(ROOT / ".env")

SCHEMA_DIR = ROOT / "database" / "schema"
SCHEMA_FILES = ["01_extensions.sql", "02_tables.sql", "03_views.sql",
                "04_simulation.sql", "05_indexes.sql"]

# Deterministic seed so demo state is reproducible; the backend engine
# re-randomises periodically at runtime.
SIM_SEED = 20260712

DSN = (
    f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')} "
    f"dbname={os.getenv('POSTGRES_DB', 'smart_city_twin')} "
    f"user={os.getenv('POSTGRES_USER', 'postgres')} "
    f"password={os.getenv('POSTGRES_PASSWORD', '')}"
)

# GeoJSON geometry sanitizer per target dimensionality:
#   ST_MakeValid repairs, ST_CollectionExtract keeps the wanted dimension,
#   ST_Multi promotes to Multi*, ST_SetSRID asserts EPSG:4326.
GEOM_POLY = "ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), 3))"
GEOM_LINE = "ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), 2))"
GEOM_POINT = "ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)"


def p(props: dict, key: str):
    return props.get(key)


THEME_LOADERS: dict[str, dict] = {
    "buildings": {
        "table": "buildings",
        "sql": f"""INSERT INTO buildings
                   (osm_type, osm_id, name, building_type, levels, height_m,
                    height_source, amenity, footprint_area_m2, geom)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,{GEOM_POLY})
                   ON CONFLICT (osm_type, osm_id) DO NOTHING""",
        "row": lambda pr: (pr.get("osm_type"), pr.get("osm_id"), pr.get("name"),
                           pr.get("building_type"), pr.get("levels"), pr.get("height_m"),
                           pr.get("height_source"), pr.get("amenity"),
                           pr.get("footprint_area_m2")),
    },
    "roads": {
        "table": "roads",
        "sql": f"""INSERT INTO roads
                   (osm_type, osm_id, name, highway, oneway, lanes, surface, maxspeed, length_m, geom)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,{GEOM_LINE})
                   ON CONFLICT (osm_type, osm_id) DO NOTHING""",
        "row": lambda pr: (pr.get("osm_type"), pr.get("osm_id"), pr.get("name"),
                           pr.get("highway"), pr.get("oneway", False), pr.get("lanes"),
                           pr.get("surface"), pr.get("maxspeed"), pr.get("length_m")),
    },
    "railways": {
        "table": "railways",
        "sql": f"""INSERT INTO railways (osm_type, osm_id, name, railway, gauge, length_m, geom)
                   VALUES (%s,%s,%s,%s,%s,%s,{GEOM_LINE})
                   ON CONFLICT (osm_type, osm_id) DO NOTHING""",
        "row": lambda pr: (pr.get("osm_type"), pr.get("osm_id"), pr.get("name"),
                           pr.get("railway"), pr.get("gauge"), pr.get("length_m")),
    },
    "waterways": {
        "table": "waterways",
        "sql": f"""INSERT INTO waterways (osm_type, osm_id, name, waterway, length_m, geom)
                   VALUES (%s,%s,%s,%s,%s,{GEOM_LINE})
                   ON CONFLICT (osm_type, osm_id) DO NOTHING""",
        "row": lambda pr: (pr.get("osm_type"), pr.get("osm_id"), pr.get("name"),
                           pr.get("waterway"), pr.get("length_m")),
    },
    "water_bodies": {
        "table": "water_bodies",
        "sql": f"""INSERT INTO water_bodies (osm_type, osm_id, name, landuse, "natural", area_m2, geom)
                   VALUES (%s,%s,%s,%s,%s,%s,{GEOM_POLY})
                   ON CONFLICT (osm_type, osm_id) DO NOTHING""",
        "row": lambda pr: (pr.get("osm_type"), pr.get("osm_id"), pr.get("name"),
                           pr.get("landuse"), pr.get("natural"), pr.get("area_m2")),
    },
    "landuse": {
        "table": "landuse",
        "sql": f"""INSERT INTO landuse (osm_type, osm_id, name, landuse, leisure, "natural", area_m2, geom)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,{GEOM_POLY})
                   ON CONFLICT (osm_type, osm_id) DO NOTHING""",
        "row": lambda pr: (pr.get("osm_type"), pr.get("osm_id"), pr.get("name"),
                           pr.get("landuse"), pr.get("leisure"), pr.get("natural"),
                           pr.get("area_m2")),
    },
    "green_spaces": {
        "table": "green_spaces",
        "sql": f"""INSERT INTO green_spaces (osm_type, osm_id, name, landuse, leisure, "natural", area_m2, geom)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,{GEOM_POLY})
                   ON CONFLICT (osm_type, osm_id) DO NOTHING""",
        "row": lambda pr: (pr.get("osm_type"), pr.get("osm_id"), pr.get("name"),
                           pr.get("landuse"), pr.get("leisure"), pr.get("natural"),
                           pr.get("area_m2")),
    },
}

# facility theme -> facility_type value
FACILITY_TYPES = {
    "hospitals": "hospital",
    "police_stations": "police_station",
    "fire_stations": "fire_station",
    "schools": "school",
    "fuel_stations": "fuel_station",
    "ev_charging": "ev_charging",
    "bus_stops": "bus_stop",
    "parking": "parking",
    "railway_stations": "railway_station",
}

FACILITY_SQL = f"""INSERT INTO facilities
    (osm_type, osm_id, facility_type, name, operator, opening_hours, capacity, beds, geom)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,{GEOM_POINT})
    ON CONFLICT (osm_type, osm_id, facility_type) DO NOTHING"""


def apply_schema(conn: psycopg.Connection) -> None:
    for filename in SCHEMA_FILES:
        sql = (SCHEMA_DIR / filename).read_text(encoding="utf-8")
        logger.info("Applying schema: %s", filename)
        conn.execute(sql)
    conn.commit()


def load_theme(conn: psycopg.Connection, theme: str) -> int:
    path = PROCESSED_DIR / f"{theme}.geojson"
    if not path.exists():
        logger.warning("Skipping %s: %s not found (run process_data.py first)", theme, path.name)
        return 0
    collection = load_geojson(path)
    features = collection["features"]

    with conn.cursor() as cur:
        if theme in FACILITY_TYPES:
            ftype = FACILITY_TYPES[theme]
            cur.execute("DELETE FROM facilities WHERE facility_type = %s", (ftype,))
            rows = [
                (f["properties"].get("osm_type"), f["properties"].get("osm_id"), ftype,
                 f["properties"].get("name"), f["properties"].get("operator"),
                 f["properties"].get("opening_hours"), f["properties"].get("capacity"),
                 f["properties"].get("beds"), json.dumps(f["geometry"]))
                for f in features
            ]
            cur.executemany(FACILITY_SQL, rows)
        else:
            spec = THEME_LOADERS[theme]
            cur.execute(f"TRUNCATE {spec['table']} RESTART IDENTITY CASCADE")
            rows = [(*spec["row"](f["properties"]), json.dumps(f["geometry"])) for f in features]
            cur.executemany(spec["sql"], rows)
        count = cur.rowcount
    conn.commit()
    logger.info("%-18s loaded %6d features", theme, len(features))
    return len(features)


def seed_simulation(conn: psycopg.Connection) -> None:
    """Seed simulation tables with an initial, reproducible demonstration state.

    All rows are flagged is_simulated = TRUE with a fixed disclaimer -
    'Simulated for Digital Twin Demonstration'. The FastAPI simulation engine
    (Milestone 9) updates these values periodically at runtime.
    """
    rng = random.Random(SIM_SEED)
    with conn.cursor() as cur:
        cur.execute("TRUNCATE sim_traffic_status, sim_parking_status, sim_ev_status RESTART IDENTITY")

        # Traffic: major roads only (motorway..tertiary incl. links)
        cur.execute("""SELECT id FROM roads WHERE highway ~
                       '^(motorway|trunk|primary|secondary|tertiary)(_link)?$'""")
        road_ids = [r[0] for r in cur.fetchall()]
        statuses = ["low", "moderate", "high", "severe"]
        weights = [0.4, 0.3, 0.2, 0.1]
        speed = {"low": 1.0, "moderate": 0.7, "high": 0.45, "severe": 0.25}
        traffic_rows = []
        for rid in road_ids:
            st = rng.choices(statuses, weights)[0]
            traffic_rows.append((rid, st, speed[st]))
        cur.executemany(
            """INSERT INTO sim_traffic_status (road_id, status, speed_factor)
               VALUES (%s, %s, %s) ON CONFLICT (road_id) DO NOTHING""",
            traffic_rows,
        )

        # Parking occupancy
        cur.execute("SELECT id FROM facilities WHERE facility_type = 'parking'")
        parking_rows = []
        for (fid,) in cur.fetchall():
            occ = round(rng.uniform(5, 100), 1)
            st = "available" if occ < 60 else ("limited" if occ < 90 else "full")
            parking_rows.append((fid, st, occ))
        cur.executemany(
            """INSERT INTO sim_parking_status (facility_id, status, occupancy_pct)
               VALUES (%s, %s, %s) ON CONFLICT (facility_id) DO NOTHING""",
            parking_rows,
        )

        # EV chargers
        cur.execute("SELECT id FROM facilities WHERE facility_type = 'ev_charging'")
        ev_rows = [
            (fid, rng.choices(["available", "busy", "offline"], [0.6, 0.3, 0.1])[0])
            for (fid,) in cur.fetchall()
        ]
        cur.executemany(
            """INSERT INTO sim_ev_status (facility_id, status)
               VALUES (%s, %s) ON CONFLICT (facility_id) DO NOTHING""",
            ev_rows,
        )
    conn.commit()
    logger.info("Simulation seeded: %d traffic, %d parking, %d EV rows (all labelled simulated)",
                len(traffic_rows), len(parking_rows), len(ev_rows))


def print_summary(conn: psycopg.Connection) -> None:
    tables = ["buildings", "roads", "railways", "waterways", "water_bodies",
              "landuse", "green_spaces", "facilities",
              "sim_traffic_status", "sim_parking_status", "sim_ev_status"]
    logger.info("--- Database summary ---")
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT count(*) FROM {table}")  # noqa: S608 - fixed table list
            logger.info("%-20s %8d rows", table, cur.fetchone()[0])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("themes", nargs="*", help="themes to load (default: all found)")
    parser.add_argument("--apply-schema", action="store_true",
                        help="apply database/schema/01-05 SQL before loading")
    parser.add_argument("--skip-simulation", action="store_true",
                        help="do not reseed simulation tables")
    args = parser.parse_args()

    all_themes = list(THEME_LOADERS) + list(FACILITY_TYPES)
    selected = args.themes or [t for t in all_themes if (PROCESSED_DIR / f"{t}.geojson").exists()]
    unknown = [t for t in selected if t not in all_themes]
    if unknown:
        sys.exit(f"Unknown theme(s): {unknown}")
    if not selected:
        sys.exit("No processed data found. Run download_osm_data.py then process_data.py first.")

    with psycopg.connect(DSN) as conn:
        if args.apply_schema:
            apply_schema(conn)
        for theme in selected:
            load_theme(conn, theme)
        if not args.skip_simulation:
            seed_simulation(conn)
        print_summary(conn)


if __name__ == "__main__":
    main()
