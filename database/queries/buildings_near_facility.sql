-- Buildings within a radius (metres) of any facility of a given type.
-- Parameters: :ftype :radius_m
--
-- Method: ST_DWithin on geography for correct metric radius; the GIST
-- index on both geometry columns supports the expansion. Example:
-- "find buildings within 500 m of a hospital".
SELECT DISTINCT b.id,
       b.name,
       b.building_type,
       b.height_m,
       b.levels
FROM buildings b
JOIN facilities f
  ON f.facility_type = :ftype
 AND ST_DWithin(b.geom::geography, f.geom::geography, :radius_m)
ORDER BY b.id;
