-- =====================================================================
-- Islamabad 3D Urban Intelligence Digital Twin - Pakistan
-- 01: Extensions
-- Apply with:  psql -d smart_city_twin -f 01_extensions.sql
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- Confirm versions (informational)
SELECT version(), PostGIS_Full_Version();
