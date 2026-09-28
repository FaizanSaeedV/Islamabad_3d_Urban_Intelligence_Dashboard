"""Advanced spatial analysis: grid-based accessibility & density, green-space
statistics, and parameterised spatial queries.

Methodology (full write-up in docs/GIS_METHODOLOGY.md):
- All grids are generated in EPSG:32643 (UTM zone 43N) so cells are true squares in
  metres; results are transformed back to EPSG:4326 for delivery.
- Green-space distance uses KNN pre-selection (5 candidates via the spatial
  index) followed by exact metric distance - a standard accuracy/performance
  compromise documented per endpoint.
- Building density uses O(n) arithmetic binning of building centroids rather
  than a polygon join, which is exact for centroid-in-cell membership.
"""

from app.core import db
from app.core.config import get_settings

_settings = get_settings()
BBOX = (
    _settings.study_area_west, _settings.study_area_south,
    _settings.study_area_east, _settings.study_area_north,
)


def green_space_point_stats(lon: float, lat: float, radius_m: float) -> dict:
    """Distance to nearest green space + count/area within radius of a point."""
    row = db.fetch_one(
        """
        WITH pt AS (SELECT ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326) AS geom)
        SELECT
          (SELECT round(ST_Distance(g.geom::geography, pt.geom::geography)::numeric, 1)
           FROM green_spaces g, pt
           ORDER BY g.geom <-> pt.geom LIMIT 1)                      AS nearest_m,
          (SELECT name FROM green_spaces g, pt
           ORDER BY g.geom <-> pt.geom LIMIT 1)                      AS nearest_name,
          (SELECT count(*) FROM green_spaces g, pt
           WHERE ST_DWithin(g.geom::geography, pt.geom::geography, %(radius)s))
                                                                     AS count_within,
          (SELECT coalesce(round((sum(g.area_m2) / 10000.0)::numeric, 2), 0)
           FROM green_spaces g, pt
           WHERE ST_DWithin(g.geom::geography, pt.geom::geography, %(radius)s))
                                                                     AS area_ha_within
        FROM pt
        """,
        {"lon": lon, "lat": lat, "radius": radius_m},
    )
    return {
        "origin": {"lon": lon, "lat": lat},
        "radius_m": radius_m,
        "nearest_green_space_m": float(row["nearest_m"]) if row and row["nearest_m"] is not None else None,
        "nearest_green_space_name": row["nearest_name"] if row else None,
        "green_spaces_within_radius": row["count_within"] if row else 0,
        "green_area_ha_within_radius": float(row["area_ha_within"]) if row else 0.0,
        "method": (
            "Nearest: KNN + exact geodesic distance. Radius counts: ST_DWithin "
            "on geography (metres)."
        ),
    }


def green_access_grid(cell_m: float = 250) -> dict:
    """Square-grid accessibility surface: distance from each cell centroid to
    the nearest green space. Cells are true metric squares (EPSG:32643)."""
    row = db.fetch_one(
        """
        WITH bounds AS (
            SELECT ST_Transform(
                ST_MakeEnvelope(%(w)s, %(s)s, %(e)s, %(n)s, 4326), 32643) AS env
        ),
        grid AS (
            SELECT (ST_SquareGrid(%(cell)s, env)).geom AS cell FROM bounds
        ),
        cells AS (
            SELECT g.cell, ST_Centroid(g.cell) AS c
            FROM grid g, bounds b
            WHERE ST_Intersects(g.cell, b.env)
        ),
        scored AS (
            SELECT cell,
                   (SELECT round(min(ST_Distance(ST_Transform(gs.geom, 32643), cells.c))::numeric, 0)
                    FROM (SELECT geom FROM green_spaces
                          ORDER BY geom <-> ST_Transform(cells.c, 4326)
                          LIMIT 5) gs) AS distance_m
            FROM cells
        )
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', coalesce(json_agg(json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(cell, 4326), 6)::json,
                'properties', json_build_object('distance_m', distance_m)
            )), '[]'::json),
            'metadata', json_build_object(
                'analysis', 'green_space_accessibility_grid',
                'cell_m', %(cell)s,
                'crs_analysis', 'EPSG:32643',
                'method', 'KNN(5) pre-selection + exact metric distance from cell centroid'
            )
        ) AS fc
        FROM scored
        """,
        {"w": BBOX[0], "s": BBOX[1], "e": BBOX[2], "n": BBOX[3], "cell": cell_m},
    )
    return row["fc"]


def building_density_grid(cell_m: float = 250) -> dict:
    """Building density + mean height per metric grid cell (arithmetic binning
    of building centroids in EPSG:32643 - exact and O(n))."""
    row = db.fetch_one(
        """
        WITH bounds AS (
            SELECT ST_Transform(
                ST_MakeEnvelope(%(w)s, %(s)s, %(e)s, %(n)s, 4326), 32643) AS env
        ),
        ext AS (SELECT ST_XMin(env) AS x0, ST_YMin(env) AS y0 FROM bounds),
        pts AS (
            SELECT ST_Transform(ST_Centroid(geom), 32643) AS p, height_m
            FROM buildings
        ),
        binned AS (
            SELECT floor((ST_X(p) - x0) / %(cell)s)::int AS i,
                   floor((ST_Y(p) - y0) / %(cell)s)::int AS j,
                   count(*) AS n,
                   round(avg(height_m)::numeric, 1) AS avg_height_m
            FROM pts, ext
            GROUP BY 1, 2
        )
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', coalesce(json_agg(json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(ST_MakeEnvelope(
                    x0 + i * %(cell)s, y0 + j * %(cell)s,
                    x0 + (i + 1) * %(cell)s, y0 + (j + 1) * %(cell)s, 32643), 4326), 6)::json,
                'properties', json_build_object('count', n, 'avg_height_m', avg_height_m)
            )), '[]'::json),
            'metadata', json_build_object(
                'analysis', 'building_density_grid',
                'cell_m', %(cell)s,
                'crs_analysis', 'EPSG:32643',
                'method', 'centroid binning per metric square cell'
            )
        ) AS fc
        FROM binned, ext
        """,
        {"w": BBOX[0], "s": BBOX[1], "e": BBOX[2], "n": BBOX[3], "cell": cell_m},
    )
    return row["fc"]


# ---------------------------------------------------------------------------
# Spatial query tool
# ---------------------------------------------------------------------------

def buildings_near_facility(facility_type: str, radius_m: float, limit: int = 5000) -> dict:
    """Buildings within radius_m (geography metres) of any facility of a type."""
    row = db.fetch_one(
        """
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', coalesce(json_agg(json_build_object(
                'type', 'Feature', 'id', sub.id,
                'geometry', ST_AsGeoJSON(sub.geom, 6)::json,
                'properties', json_build_object(
                    'name', sub.name, 'building_type', sub.building_type,
                    'height_m', sub.height_m, 'levels', sub.levels)
            )), '[]'::json)
        ) AS fc
        FROM (
            SELECT DISTINCT b.id, b.name, b.building_type, b.height_m, b.levels, b.geom
            FROM buildings b
            JOIN facilities f
              ON f.facility_type = %(ftype)s
             AND ST_DWithin(b.geom::geography, f.geom::geography, %(radius)s)
            ORDER BY b.id
            LIMIT %(limit)s
        ) sub
        """,
        {"ftype": facility_type, "radius": radius_m, "limit": limit},
    )
    return row["fc"]


def facilities_within(lon: float, lat: float, radius_m: float,
                      facility_type: str | None = None) -> dict:
    """Facilities within radius_m of a point, optionally filtered by type."""
    type_clause = "AND facility_type = %(ftype)s" if facility_type else ""
    row = db.fetch_one(
        f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', coalesce(json_agg(json_build_object(
                'type', 'Feature', 'id', sub.id,
                'geometry', ST_AsGeoJSON(sub.geom, 6)::json,
                'properties', json_build_object(
                    'name', sub.name, 'facility_type', sub.facility_type,
                    'distance_m', sub.distance_m)
            )), '[]'::json)
        ) AS fc
        FROM (
            SELECT id, name, facility_type, geom,
                   round(ST_Distance(geom::geography,
                       ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography)::numeric, 1)
                       AS distance_m
            FROM facilities
            WHERE ST_DWithin(geom::geography,
                  ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography, %(radius)s)
            {type_clause}
            ORDER BY distance_m
            LIMIT 2000
        ) sub
        """,  # noqa: S608 - type_clause is a fixed string, value is parameterised
        {"lon": lon, "lat": lat, "radius": radius_m, "ftype": facility_type},
    )
    return row["fc"]


MAJOR_ROAD_CLASSES = ["motorway", "trunk", "primary", "secondary"]


def facilities_near_major_roads(facility_type: str, radius_m: float) -> dict:
    """Facilities of a type within radius_m of a major road (e.g. schools)."""
    row = db.fetch_one(
        """
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', coalesce(json_agg(json_build_object(
                'type', 'Feature', 'id', sub.id,
                'geometry', ST_AsGeoJSON(sub.geom, 6)::json,
                'properties', json_build_object(
                    'name', sub.name, 'facility_type', sub.facility_type)
            )), '[]'::json)
        ) AS fc
        FROM (
            SELECT f.id, f.name, f.facility_type, f.geom
            FROM facilities f
            WHERE f.facility_type = %(ftype)s
              AND EXISTS (
                  SELECT 1 FROM roads r
                  WHERE r.highway = ANY(%(classes)s)
                    AND ST_DWithin(f.geom::geography, r.geom::geography, %(radius)s))
            ORDER BY f.id
            LIMIT 2000
        ) sub
        """,
        {"ftype": facility_type, "radius": radius_m, "classes": MAJOR_ROAD_CLASSES},
    )
    return row["fc"]
