# Data Sources

Every dataset in this project is free and open. Nothing is fabricated; estimated or simulated values are explicitly flagged in data and UI.

## Primary sources

| Source | Data used | Access method | License | Key required |
|---|---|---|---|---|
| **OpenStreetMap** | Buildings, roads, railways, water, land use, green spaces, all 9 facility types | Overpass API (3 mirror endpoints) | ODbL 1.0 | No |
| **Open-Meteo** | Current weather for Islamabad | REST (`/v1/forecast`) | CC BY 4.0 | No |
| **Project OSRM** | Road-network routing | Public demo server | BSD 2-Clause (data: ODbL) | No |
| **OSM Nominatim** | Place search (frontend, bounded to Islamabad) | REST | ODbL; usage policy ≤1 req/s | No |
| **Cesium ion** *(optional)* | World Terrain | CesiumJS | Free tier | Free account token |

Natural Earth (public domain) is an approved fallback for context layers; the current build derives everything from OSM. Copernicus/Sentinel imagery is listed as a future improvement (land-cover classification) — not used in the current analyses.

## Generated data (clearly labelled)

| Dataset | Nature | Labelling |
|---|---|---|
| `sim_traffic_status`, `sim_parking_status`, `sim_ev_status` | Synthetic demonstration state, seeded Markov process | `is_simulated=TRUE` CHECK constraint + fixed disclaimer column; UI banners and popup warnings |
| Building heights where untagged | Estimate (levels × 3 m, or 6 m default) | `height_source` flag; labelled "estimated"/"assumed" in UI |
| `tests/fixtures/synthetic_buildings_fixture.geojson` | Synthetic test fixture | Header states it must never be loaded into the app database |

## Attribution requirements

Reproduce these when reusing the project:

> Map data © OpenStreetMap contributors, ODbL — openstreetmap.org/copyright
> Weather data by Open-Meteo.com (CC BY 4.0)
> Routing by Project OSRM demo server

## Data quality notes

OSM completeness in Islamabad is good for roads and major facilities, weaker for building attributes (heights/levels mostly untagged) and opening hours. EV-charging coverage in OSM is sparse and likely undercounts reality. Download date matters: re-running the pipeline captures the current OSM state; `processing_report.json` records counts per run. See `docs/LIMITATIONS.md`.
