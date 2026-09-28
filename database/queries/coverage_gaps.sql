-- Service-coverage analysis: dissolved buffer around all facilities of a
-- type, and the share of buildings outside it (underserved).
-- Parameters: :ftype :radius_m
--
-- Method: buffers are generated in EPSG:32643 (metric, low distortion over
-- Islamabad), dissolved with ST_Union, then intersected against building
-- centroids transformed to the same CRS. Buffering in a projected CRS
-- avoids the invalid "degree buffers" anti-pattern.
WITH service_area AS (
    SELECT ST_Union(ST_Buffer(ST_Transform(geom, 32643), :radius_m)) AS geom
    FROM facilities
    WHERE facility_type = :ftype
)
SELECT count(*)                                            AS total_buildings,
       count(*) FILTER (WHERE NOT ST_Intersects(
           ST_Transform(ST_Centroid(b.geom), 32643), s.geom)) AS underserved_buildings,
       round(100.0 * count(*) FILTER (WHERE NOT ST_Intersects(
           ST_Transform(ST_Centroid(b.geom), 32643), s.geom)) / count(*), 1)
                                                           AS underserved_pct
FROM buildings b
CROSS JOIN service_area s;
