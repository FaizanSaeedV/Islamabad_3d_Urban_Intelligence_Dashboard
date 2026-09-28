"""GeoJSON layer queries. Builds RFC 7946 FeatureCollections inside PostGIS
(json_build_object + ST_AsGeoJSON) for efficiency - one row per response."""

from app.core import db

# Whitelisted layer definitions: table -> (columns for properties, geometry column)
# Only these identifiers ever reach SQL; user input never becomes an identifier.
LAYERS: dict[str, dict] = {
    "buildings": {
        "table": "buildings",
        "columns": ["osm_id", "name", "building_type", "levels", "height_m",
                    "height_source", "amenity", "footprint_area_m2"],
    },
    "roads": {
        "table": "roads",
        "columns": ["osm_id", "name", "highway", "oneway", "lanes", "maxspeed", "length_m"],
    },
    "railways": {
        "table": "railways",
        "columns": ["osm_id", "name", "railway", "length_m"],
    },
    "waterways": {
        "table": "waterways",
        "columns": ["osm_id", "name", "waterway", "length_m"],
    },
    "water_bodies": {
        "table": "water_bodies",
        "columns": ["osm_id", "name", "natural", "area_m2"],
    },
    "landuse": {
        "table": "landuse",
        "columns": ["osm_id", "name", "landuse", "leisure", "natural", "area_m2"],
    },
    "green_spaces": {
        "table": "green_spaces",
        "columns": ["osm_id", "name", "landuse", "leisure", "natural", "area_m2"],
    },
}

FACILITY_COLUMNS = ["osm_id", "facility_type", "name", "operator",
                    "opening_hours", "capacity", "beds"]

# ~metres -> degrees at the equator; adequate for simplification tolerance
_M_TO_DEG = 1.0 / 111_320.0


def _collection_sql(table: str, columns: list[str], where: str, simplify_m: float | None) -> str:
    cols = ", ".join(f'"{c}"' for c in columns)
    geom_expr = "geom"
    if simplify_m:
        geom_expr = f"ST_SimplifyPreserveTopology(geom, {simplify_m * _M_TO_DEG:.8f})"
    return f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', coalesce(json_agg(json_build_object(
                'type', 'Feature',
                'id', sub.id,
                'geometry', ST_AsGeoJSON(sub.g, 6)::json,
                'properties', to_jsonb(sub) - 'g' - 'id'
            )), '[]'::json)
        ) AS fc
        FROM (
            SELECT id, {cols}, {geom_expr} AS g
            FROM {table}
            {where}
        ) sub
    """  # noqa: S608 - table/columns come from the whitelist above


def get_layer(
    layer: str,
    bbox: tuple[float, float, float, float] | None = None,
    limit: int = 100_000,
    simplify_m: float | None = None,
) -> dict:
    """Return a layer as a GeoJSON FeatureCollection dict.

    bbox: (west, south, east, north) in EPSG:4326.
    """
    spec = LAYERS[layer]
    params: dict = {"limit": limit}
    clauses = []
    if bbox:
        clauses.append(
            "geom && ST_MakeEnvelope(%(w)s, %(s)s, %(e)s, %(n)s, 4326)"
        )
        params.update({"w": bbox[0], "s": bbox[1], "e": bbox[2], "n": bbox[3]})
    where = ("WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY id LIMIT %(limit)s"
    row = db.fetch_one(_collection_sql(spec["table"], spec["columns"], where, simplify_m), params)
    return row["fc"]


def get_facilities(facility_type: str | None = None, limit: int = 20_000) -> dict:
    """Facilities as GeoJSON, optionally filtered by type (validated upstream)."""
    params: dict = {"limit": limit}
    where = ""
    if facility_type:
        where = "WHERE facility_type = %(ftype)s"
        params["ftype"] = facility_type
    where += " ORDER BY id LIMIT %(limit)s"
    row = db.fetch_one(_collection_sql("facilities", FACILITY_COLUMNS, where, None), params)
    return row["fc"]


def layer_names() -> list[str]:
    return list(LAYERS)
