-- =====================================================================
-- Smart City Digital Twin - 05: Indexes
-- GIST spatial indexes on every geometry column; b-tree attribute
-- indexes on frequent filter columns.
-- =====================================================================

-- Spatial (GIST)
CREATE INDEX IF NOT EXISTS idx_buildings_geom     ON buildings     USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_roads_geom         ON roads         USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_railways_geom      ON railways      USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_waterways_geom     ON waterways     USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_water_bodies_geom  ON water_bodies  USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_landuse_geom       ON landuse       USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_green_spaces_geom  ON green_spaces  USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_facilities_geom    ON facilities    USING GIST (geom);

-- Attribute (b-tree)
CREATE INDEX IF NOT EXISTS idx_facilities_type    ON facilities (facility_type);
CREATE INDEX IF NOT EXISTS idx_roads_highway      ON roads (highway);
CREATE INDEX IF NOT EXISTS idx_buildings_type     ON buildings (building_type);
CREATE INDEX IF NOT EXISTS idx_buildings_height   ON buildings (height_m);
CREATE INDEX IF NOT EXISTS idx_landuse_class      ON landuse (landuse);

-- Simulation lookups
CREATE INDEX IF NOT EXISTS idx_sim_traffic_road   ON sim_traffic_status (road_id);
CREATE INDEX IF NOT EXISTS idx_sim_parking_fac    ON sim_parking_status (facility_id);
CREATE INDEX IF NOT EXISTS idx_sim_ev_fac         ON sim_ev_status (facility_id);

ANALYZE;
