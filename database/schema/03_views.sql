-- =====================================================================
-- Smart City Digital Twin - 03: Facility views
-- Typed access to the facilities table, one view per facility class.
-- =====================================================================

CREATE OR REPLACE VIEW v_hospitals AS
    SELECT id, osm_type, osm_id, name, operator, opening_hours, beds, geom
    FROM facilities WHERE facility_type = 'hospital';

CREATE OR REPLACE VIEW v_police_stations AS
    SELECT id, osm_type, osm_id, name, operator, opening_hours, geom
    FROM facilities WHERE facility_type = 'police_station';

CREATE OR REPLACE VIEW v_fire_stations AS
    SELECT id, osm_type, osm_id, name, operator, opening_hours, geom
    FROM facilities WHERE facility_type = 'fire_station';

CREATE OR REPLACE VIEW v_schools AS
    SELECT id, osm_type, osm_id, name, operator, opening_hours, geom
    FROM facilities WHERE facility_type = 'school';

CREATE OR REPLACE VIEW v_fuel_stations AS
    SELECT id, osm_type, osm_id, name, operator, opening_hours, geom
    FROM facilities WHERE facility_type = 'fuel_station';

CREATE OR REPLACE VIEW v_ev_charging AS
    SELECT id, osm_type, osm_id, name, operator, opening_hours, capacity, geom
    FROM facilities WHERE facility_type = 'ev_charging';

CREATE OR REPLACE VIEW v_bus_stops AS
    SELECT id, osm_type, osm_id, name, operator, geom
    FROM facilities WHERE facility_type = 'bus_stop';

CREATE OR REPLACE VIEW v_parking AS
    SELECT id, osm_type, osm_id, name, operator, capacity, geom
    FROM facilities WHERE facility_type = 'parking';

CREATE OR REPLACE VIEW v_railway_stations AS
    SELECT id, osm_type, osm_id, name, operator, geom
    FROM facilities WHERE facility_type = 'railway_station';
