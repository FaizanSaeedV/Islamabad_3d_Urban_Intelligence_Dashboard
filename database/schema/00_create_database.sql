-- =====================================================================
-- Smart City Digital Twin - 00: Database creation
-- Run as the postgres superuser, connected to the default database:
--   psql -U postgres -f 00_create_database.sql
-- Then apply 01..05 connected to smart_city_twin:
--   psql -U postgres -d smart_city_twin -f 01_extensions.sql   (etc.)
-- =====================================================================

CREATE DATABASE smart_city_twin
    WITH ENCODING 'UTF8'
    TEMPLATE template0;
