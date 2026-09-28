-- Distance from a point to the nearest green space and count within radius.
-- Parameters: :lon :lat :radius_m
--
-- Method: KNN pre-selection on the geometry index, exact edge-to-point
-- distance on geography (distance to polygon boundary/interior = 0 if
-- inside). Used by the green-space accessibility module.
WITH pt AS (
    SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS geom
)
SELECT
    (SELECT ST_Distance(g.geom::geography, pt.geom::geography)
     FROM green_spaces g, pt
     ORDER BY g.geom <-> pt.geom
     LIMIT 1)                                              AS nearest_green_space_m,
    (SELECT count(*)
     FROM green_spaces g, pt
     WHERE ST_DWithin(g.geom::geography, pt.geom::geography, :radius_m))
                                                           AS green_spaces_within_radius,
    (SELECT coalesce(sum(g.area_m2), 0)
     FROM green_spaces g, pt
     WHERE ST_DWithin(g.geom::geography, pt.geom::geography, :radius_m))
                                                           AS green_area_m2_within_radius
FROM pt;
