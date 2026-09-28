# Known Limitations

An honest account of what this project does *not* do. Each limitation is a deliberate, documented trade-off within a free/open-data scope — not an oversight.

## Data

1. **Building heights are mostly estimated.** Few Islamabad buildings carry OSM `height`/`levels` tags; the flagged estimation rule (levels × 3 m, 6 m default) is documented in `GIS_METHODOLOGY.md` and visible per building in the UI. Absolute heights are indicative, not survey-grade.
2. **OSM completeness varies.** Facility coverage is strong for hospitals/schools, weak for EV chargers; attributes (capacity, beds, opening hours) are sparse. Analyses describe the *mapped* city.
3. **Snapshot data.** The pipeline captures OSM at download time; no automatic sync. Re-run the pipeline to refresh.
4. **Multipolygon holes** in complex relations are handled by ring polygonisation; a small number of exotic relations may simplify to outer rings.

## Analysis

5. **Straight-line accessibility.** Green-space and coverage analyses use Euclidean/geodesic distance, not walking-network distance; real access is longer where canals, rail lines, or arterials intervene.
6. **MAUP.** Grid analyses depend on cell size (user-selectable 100–1000 m) and origin; patterns, not precise values, are the takeaway.
7. **Free-flow travel times.** OSRM demo durations ignore live traffic — materially optimistic for Islamabad peaks. The simulated traffic layer is display-only and never feeds routing.
8. **Equal facility weighting.** Coverage treats a clinic like a national hospital; no capacity weighting (data rarely available).
9. **Edge effects.** Facilities just outside the study bbox are invisible to nearest/coverage analyses near the boundary.

## Simulation

10. **The digital twin's "real-time" layers are simulations.** Traffic, parking, and EV states are a seeded Markov process, labelled *"Simulated for Digital Twin Demonstration"* at database (CHECK constraint), API, and UI level. No claim of real telemetry is made anywhere.

## Technical

11. **No photogrammetric 3D.** Buildings are extruded footprints (LoD1); the height "measurement" tool therefore reports attributes, and says so.
12. **Ellipsoid terrain by default.** Islamabad is near sea level so distortion is minor; a free Cesium ion token enables World Terrain.
13. **Free-tier deployment constraints.** Render sleeps after inactivity (~30–60 s cold start); OSRM demo and Nominatim are rate-limited public services without SLA.
14. **Large-payload layers.** Buildings/roads GeoJSON can reach tens of MB; mitigations (bbox, limits, server-side simplification, lazy loading) are in place, but a tiled pipeline (3D Tiles / vector tiles) is the proper scaling path — listed as future work.
15. **Measurement approximations.** Distance is geodesic on the ellipsoid (terrain ignored); area uses a local tangent plane (<0.1 % error at city scale; not for large extents).
