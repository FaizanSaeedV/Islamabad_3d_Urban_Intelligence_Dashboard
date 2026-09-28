"""Server-side spatial analysis: nearest facility, coverage, analytics.

CRS policy: KNN candidate selection uses the geometry index (degrees) but is
always re-ranked by exact metric distance - either WGS 84 geography (geodesic)
or EPSG:32643 (UTM zone 43N planar) as documented per function.
"""

from datetime import datetime, timezone

from app.core import db

# Building height classification (documented in docs/GIS_METHODOLOGY.md):
# thresholds follow common urban-morphology practice - low-rise < 12 m
# (~<=3-4 storeys), mid-rise 12-30 m, high-rise > 30 m.
HEIGHT_CLASSES = [("low_rise", 0, 12), ("mid_rise", 12, 30), ("high_rise", 30, 10_000)]


def nearest_facilities(lon: float, lat: float, facility_type: str, n: int = 5) -> list[dict]:
    """K nearest facilities: KNN pre-selection + exact geodesic re-ranking."""
    return db.fetch_all(
        """
        SELECT id, name, facility_type,
               ST_X(geom) AS lon, ST_Y(geom) AS lat,
               round(ST_Distance(geom::geography,
                     ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography)::numeric, 1)
                   AS distance_m
        FROM (
            SELECT * FROM facilities
            WHERE facility_type = %(ftype)s
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)
            LIMIT 50
        ) candidates
        ORDER BY distance_m
        LIMIT %(n)s
        """,
        {"lon": lon, "lat": lat, "ftype": facility_type, "n": n},
    )


def straight_line_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Geodesic distance between two points (WGS 84 geography)."""
    row = db.fetch_one(
        """
        SELECT round(ST_Distance(
            ST_SetSRID(ST_MakePoint(%(x1)s, %(y1)s), 4326)::geography,
            ST_SetSRID(ST_MakePoint(%(x2)s, %(y2)s), 4326)::geography)::numeric, 1) AS d
        """,
        {"x1": lon1, "y1": lat1, "x2": lon2, "y2": lat2},
    )
    return float(row["d"])


def coverage(facility_type: str, radius_m: float, include_geometry: bool = True) -> dict:
    """Service coverage: dissolved EPSG:32643 buffers vs building centroids."""
    stats = db.fetch_one(
        """
        WITH service_area AS (
            SELECT ST_Union(ST_Buffer(ST_Transform(geom, 32643), %(radius)s)) AS geom,
                   count(*) AS n_fac
            FROM facilities
            WHERE facility_type = %(ftype)s
        )
        SELECT s.n_fac AS facility_count,
               count(b.id) AS total_buildings,
               count(b.id) FILTER (WHERE s.geom IS NOT NULL AND ST_Intersects(
                   ST_Transform(ST_Centroid(b.geom), 32643), s.geom)) AS covered_buildings
        FROM buildings b
        CROSS JOIN service_area s
        GROUP BY s.n_fac
        """,
        {"ftype": facility_type, "radius": radius_m},
    )
    if stats is None:  # no buildings loaded
        stats = {"facility_count": 0, "total_buildings": 0, "covered_buildings": 0}

    total = stats["total_buildings"] or 0
    covered = stats["covered_buildings"] or 0
    underserved = total - covered

    service_area_geojson = None
    if include_geometry and stats["facility_count"]:
        row = db.fetch_one(
            """
            SELECT ST_AsGeoJSON(
                ST_Transform(
                    ST_SimplifyPreserveTopology(
                        ST_Union(ST_Buffer(ST_Transform(geom, 32643), %(radius)s)), 25),
                    4326), 6)::json AS gj
            FROM facilities
            WHERE facility_type = %(ftype)s
            """,
            {"ftype": facility_type, "radius": radius_m},
        )
        service_area_geojson = row["gj"] if row else None

    return {
        "facility_type": facility_type,
        "radius_m": radius_m,
        "facility_count": stats["facility_count"],
        "total_buildings": total,
        "covered_buildings": covered,
        "underserved_buildings": underserved,
        "underserved_pct": round(100.0 * underserved / total, 1) if total else 0.0,
        "service_area": service_area_geojson,
    }


def analytics() -> dict:
    """Urban statistics for the dashboard (single round trip per chart)."""
    totals_row = db.fetch_one(
        """
        SELECT
          (SELECT count(*) FROM buildings)                                    AS total_buildings,
          (SELECT coalesce(round(sum(length_m) / 1000.0, 1), 0) FROM roads)   AS road_length_km,
          (SELECT coalesce(round(sum(length_m) / 1000.0, 1), 0) FROM railways) AS railway_length_km,
          (SELECT count(*) FROM facilities WHERE facility_type = 'hospital')  AS hospitals,
          (SELECT count(*) FROM facilities WHERE facility_type = 'school')    AS schools,
          (SELECT count(*) FROM facilities WHERE facility_type = 'fuel_station') AS fuel_stations,
          (SELECT count(*) FROM facilities WHERE facility_type = 'ev_charging')  AS ev_charging_stations,
          (SELECT count(*) FROM facilities WHERE facility_type = 'parking')   AS parking_locations,
          (SELECT count(*) FROM facilities WHERE facility_type = 'bus_stop')  AS bus_stops,
          (SELECT count(*) FROM green_spaces)                                 AS green_spaces,
          (SELECT coalesce(round(sum(area_m2) / 10000.0, 1), 0) FROM green_spaces) AS green_area_ha,
          (SELECT coalesce(round(sum(area_m2) / 10000.0, 1), 0) FROM water_bodies) AS water_area_ha
        """
    )

    height_rows = db.fetch_all(
        """
        SELECT CASE
                 WHEN height_m < 12 THEN 'Low-rise (<12 m)'
                 WHEN height_m < 30 THEN 'Mid-rise (12-30 m)'
                 ELSE 'High-rise (>30 m)'
               END AS cls,
               count(*) AS n
        FROM buildings
        GROUP BY 1
        ORDER BY min(height_m)
        """
    )

    type_rows = db.fetch_all(
        """
        SELECT coalesce(nullif(building_type, ''), 'unspecified') AS t, count(*) AS n
        FROM buildings GROUP BY 1 ORDER BY n DESC LIMIT 8
        """
    )

    facility_rows = db.fetch_all(
        "SELECT facility_type AS t, count(*) AS n FROM facilities GROUP BY 1 ORDER BY n DESC"
    )

    landuse_rows = db.fetch_all(
        """
        SELECT coalesce(landuse, leisure, "natural", 'other') AS t,
               round(sum(area_m2) / 10000.0, 1) AS ha
        FROM landuse GROUP BY 1 ORDER BY ha DESC LIMIT 8
        """
    )

    mobility_rows = db.fetch_all(
        """
        SELECT facility_type AS t, count(*) AS n FROM facilities
        WHERE facility_type IN ('bus_stop', 'railway_station', 'fuel_station',
                                'ev_charging', 'parking')
        GROUP BY 1 ORDER BY n DESC
        """
    )

    def chart(rows, label_key, value_key):
        return {
            "labels": [str(r[label_key]) for r in rows],
            "values": [float(r[value_key]) for r in rows],
        }

    return {
        "generated_at": datetime.now(timezone.utc),
        "totals": {k: float(v) for k, v in (totals_row or {}).items()},
        "building_height_classes": chart(height_rows, "cls", "n"),
        "building_types": chart(type_rows, "t", "n"),
        "facility_distribution": chart(facility_rows, "t", "n"),
        "landuse_distribution": chart(landuse_rows, "t", "ha"),
        "mobility_infrastructure": chart(mobility_rows, "t", "n"),
    }
