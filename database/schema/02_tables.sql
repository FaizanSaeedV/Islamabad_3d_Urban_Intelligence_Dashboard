-- =====================================================================
-- Islamabad 3D Urban Intelligence Digital Twin - Pakistan
-- 02: Core spatial tables
--
-- CRS policy:
--   * Geometries are STORED in EPSG:4326 (WGS 84) - native OSM/GeoJSON/Cesium CRS.
--   * Metric distance/area/buffer operations TRANSFORM to EPSG:32643
--     (WGS 84 / UTM zone 43N) inside queries - never computed in degrees.
--
-- Source data: OpenStreetMap (c) OpenStreetMap contributors, ODbL 1.0,
-- processed by scripts/process_data.py. Estimated attributes (e.g. building
-- height) carry an explicit *_source column - nothing estimated is presented
-- as measured.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Buildings (extruded in the 3D viewer)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS buildings (
    id                 BIGSERIAL PRIMARY KEY,
    osm_type           TEXT        NOT NULL,
    osm_id             BIGINT      NOT NULL,
    name               TEXT,
    building_type      TEXT,
    levels             INTEGER     CHECK (levels IS NULL OR levels BETWEEN 1 AND 200),
    height_m           NUMERIC(6,1) NOT NULL CHECK (height_m > 0 AND height_m <= 500),
    height_source      TEXT        NOT NULL
        CHECK (height_source IN ('osm_height', 'levels_x3', 'default_assumed')),
    amenity            TEXT,
    footprint_area_m2  NUMERIC(12,1),
    geom               geometry(MultiPolygon, 4326) NOT NULL,
    CONSTRAINT buildings_osm_uniq UNIQUE (osm_type, osm_id)
);

COMMENT ON TABLE  buildings IS 'OSM building footprints, Islamabad study area (EPSG:4326).';
COMMENT ON COLUMN buildings.height_m IS 'Metres. See height_source: osm_height = tagged; levels_x3 = levels x 3.0 m; default_assumed = 6.0 m fallback.';
COMMENT ON COLUMN buildings.footprint_area_m2 IS 'Planar area computed in EPSG:32643.';

-- ---------------------------------------------------------------------
-- Roads
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roads (
    id        BIGSERIAL PRIMARY KEY,
    osm_type  TEXT    NOT NULL,
    osm_id    BIGINT  NOT NULL,
    name      TEXT,
    highway   TEXT    NOT NULL,
    oneway    BOOLEAN DEFAULT FALSE,
    lanes     NUMERIC(4,1),
    surface   TEXT,
    maxspeed  NUMERIC(5,1),
    length_m  NUMERIC(10,1),
    geom      geometry(MultiLineString, 4326) NOT NULL,
    CONSTRAINT roads_osm_uniq UNIQUE (osm_type, osm_id)
);

COMMENT ON TABLE roads IS 'OSM highway network (EPSG:4326). length_m computed in EPSG:32643.';

-- ---------------------------------------------------------------------
-- Railways
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS railways (
    id        BIGSERIAL PRIMARY KEY,
    osm_type  TEXT   NOT NULL,
    osm_id    BIGINT NOT NULL,
    name      TEXT,
    railway   TEXT   NOT NULL,
    gauge     TEXT,
    length_m  NUMERIC(10,1),
    geom      geometry(MultiLineString, 4326) NOT NULL,
    CONSTRAINT railways_osm_uniq UNIQUE (osm_type, osm_id)
);

-- ---------------------------------------------------------------------
-- Waterways (linear: rivers, canals, streams)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS waterways (
    id        BIGSERIAL PRIMARY KEY,
    osm_type  TEXT   NOT NULL,
    osm_id    BIGINT NOT NULL,
    name      TEXT,
    waterway  TEXT   NOT NULL,
    length_m  NUMERIC(10,1),
    geom      geometry(MultiLineString, 4326) NOT NULL,
    CONSTRAINT waterways_osm_uniq UNIQUE (osm_type, osm_id)
);

-- ---------------------------------------------------------------------
-- Water bodies (polygonal: lakes, Beira Lake, reservoirs)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS water_bodies (
    id        BIGSERIAL PRIMARY KEY,
    osm_type  TEXT   NOT NULL,
    osm_id    BIGINT NOT NULL,
    name      TEXT,
    landuse   TEXT,
    "natural" TEXT,
    area_m2   NUMERIC(14,1),
    geom      geometry(MultiPolygon, 4326) NOT NULL,
    CONSTRAINT water_bodies_osm_uniq UNIQUE (osm_type, osm_id)
);

-- ---------------------------------------------------------------------
-- Land use polygons
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS landuse (
    id        BIGSERIAL PRIMARY KEY,
    osm_type  TEXT   NOT NULL,
    osm_id    BIGINT NOT NULL,
    name      TEXT,
    landuse   TEXT,
    leisure   TEXT,
    "natural" TEXT,
    area_m2   NUMERIC(14,1),
    geom      geometry(MultiPolygon, 4326) NOT NULL,
    CONSTRAINT landuse_osm_uniq UNIQUE (osm_type, osm_id)
);

-- ---------------------------------------------------------------------
-- Green spaces (parks, gardens, playgrounds, forests, meadows)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS green_spaces (
    id        BIGSERIAL PRIMARY KEY,
    osm_type  TEXT   NOT NULL,
    osm_id    BIGINT NOT NULL,
    name      TEXT,
    landuse   TEXT,
    leisure   TEXT,
    "natural" TEXT,
    area_m2   NUMERIC(14,1),
    geom      geometry(MultiPolygon, 4326) NOT NULL,
    CONSTRAINT green_spaces_osm_uniq UNIQUE (osm_type, osm_id)
);

-- ---------------------------------------------------------------------
-- Facilities: single table + typed views (03_views.sql).
-- Design note: one table with facility_type avoids nine near-identical
-- tables, keeps spatial indexing simple, and per-type views give the
-- domain-specific access the application needs.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS facilities (
    id             BIGSERIAL PRIMARY KEY,
    osm_type       TEXT   NOT NULL,
    osm_id         BIGINT NOT NULL,
    facility_type  TEXT   NOT NULL CHECK (facility_type IN (
        'hospital', 'police_station', 'fire_station', 'school',
        'fuel_station', 'ev_charging', 'bus_stop', 'parking', 'railway_station'
    )),
    name           TEXT,
    operator       TEXT,
    opening_hours  TEXT,
    capacity       NUMERIC(8,1),
    beds           NUMERIC(6,1),
    geom           geometry(Point, 4326) NOT NULL,
    CONSTRAINT facilities_osm_uniq UNIQUE (osm_type, osm_id, facility_type)
);

COMMENT ON TABLE facilities IS 'Urban facility points (polygon facilities reduced to centroids by the pipeline).';
