# Developer Guide

## Architecture in one paragraph

Static ES-module frontend (CesiumJS + Chart.js, no build step) → FastAPI backend (thin routers → services holding all SQL/logic → psycopg 3 pool) → PostGIS (storage EPSG:4326, analysis EPSG:32643). External free APIs (Open-Meteo, OSRM, Nominatim) are proxied or called client-side; a background asyncio task advances the labelled simulation state. Full diagrams: `ARCHITECTURE.md`.

## Repository map

```
backend/app/
  core/config.py      pydantic-settings (.env); SRIDs; study bbox
  core/db.py          psycopg pool (5 s fail-fast), fetch helpers, health
  routers/            HTTP layer only - validation via typing.Annotated Query
  services/           layers (GeoJSON SQL), spatial, analysis, weather, routing, simulation
  schemas/            Pydantic response models (incl. GeoJSON)
frontend/js/
  config.js           deploy config (API URL, optional ion token)
  app.js              entry point - wires everything
  modules/            viewer, ui, api, buildings, layers, mobility, emergency,
                      weather, dashboard, simulation, timeviz, analysis, query,
                      measure, mappick
database/schema/      00-05 DDL (numbered apply order)
database/queries/     documented reference SQL
scripts/              osm_common, download_osm_data, process_data, load_to_postgis
tests/                backend/, spatial/, frontend/, fixtures/, manual checklist
```

## Conventions

- **SQL safety:** identifiers only from whitelists (`services/layers.py::LAYERS`); values always parameterised (`%(name)s`). Never interpolate user input.
- **CRS:** metric maths in EPSG:32643 or geography — never in degrees. New analyses must document their choice in `GIS_METHODOLOGY.md` and add a test.
- **Honesty:** estimated attributes carry a `*_source` flag; simulated data carries `is_simulated` + disclaimer end-to-end. Preserve this in new features.
- **Errors:** 422 invalid input, 502 upstream, 503 database — handled globally in `main.py`.
- **Frontend:** one module per feature, exporting pure helpers (testable in Node without a browser) separately from DOM/Cesium wiring.

## Adding a new layer (checklist)

1. Overpass selector in `scripts/download_osm_data.py::THEMES`.
2. Normaliser in `scripts/process_data.py` (+ theme mapping).
3. Table/DDL in `database/schema/02_tables.sql` + indexes in `05` + loader spec in `load_to_postgis.py`.
4. Whitelist entry in `backend/app/services/layers.py` + router endpoint.
5. Frontend registry entry in `frontend/js/modules/layers.js::LAYER_DEFS`.
6. Tests: validation params + (if analysed) spatial assertions; update methodology doc.

## Adding an analysis endpoint

Service function in `services/analysis.py` (SQL with method comment) → router with validated params → frontend card → methodology section (7-point template) → tests (validation + result invariants, e.g. monotonicity).

## Running everything

```bash
uvicorn app.main:app --reload            # backend, from backend/
python -m http.server 5500               # frontend, from frontend/
python -m pytest                         # 40 tests (6 skip without DB)
node tests/frontend/logic_tests.mjs      # 12 logic checks
```

## Milestone commit history (suggested)

1. `feat: project architecture, FastAPI skeleton with health check, CesiumJS viewer shell for Islamabad digital twin`
2. `feat: OSM data pipeline - Overpass download (16 themes), validation, height estimation, EPSG:32643 metrics`
3. `feat: PostGIS schema with constraints and spatial indexes, idempotent loader, simulation seed, ER docs`
4. `feat: complete FastAPI backend - GeoJSON layers, nearest/route/coverage analysis, analytics, Open-Meteo weather, simulation engine with clean error contract`
5. `feat: 3D city viewer - extruded buildings with height classification and honest click-to-inspect attributes`
6. `feat: registry-driven smart city layer control - 16 lazy-loaded layers, per-class styling, honest attribute inspection`
7. `feat: mobility and emergency response modules - nearest facility search, OSRM routing, 3D response routes`
8. `feat: urban analytics dashboard with Chart.js and live Open-Meteo weather card`
9. `feat: digital twin simulation overlays with live refresh and CZML time-animated demo vehicles on real OSM routes`
10. `feat: advanced GIS analysis - metric grid density/accessibility surfaces, coverage tool, spatial query builder, 3D measurement`
11. `test: backend contract/validation suites, pipeline fixture tests, CRS + live spatial validation, frontend logic tests, manual checklist`
12. `docs: complete documentation set, GIS methodology, deployment blueprints (Render + GitHub Pages), CI workflows`
