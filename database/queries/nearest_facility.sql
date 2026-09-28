-- Nearest N facilities of a type from a point (KNN + exact geodesic distance).
-- Parameters: :lon :lat :ftype :n
--
-- Method: the <-> operator gives an index-accelerated approximate KNN
-- ordering in degrees; the outer query re-ranks the candidate set by exact
-- geography distance (metres on the WGS 84 spheroid). For short urban
-- distances geography distance and EPSG:32643 planar distance agree to
-- centimetres; geography is used here because the input point may lie
-- anywhere.
SELECT id,
       name,
       facility_type,
       ST_X(geom) AS lon,
       ST_Y(geom) AS lat,
       ST_Distance(geom::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS distance_m
FROM (
    SELECT *
    FROM facilities
    WHERE facility_type = :ftype
    ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
    LIMIT 50
) candidates
ORDER BY distance_m
LIMIT :n;
