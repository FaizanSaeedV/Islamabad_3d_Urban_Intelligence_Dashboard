# Scripts

Python data pipeline (Milestone 2):

1. `download_osm_data.py` — fetch buildings, roads, railways, facilities, water, land use, and green spaces for the Islamabad study area from the OpenStreetMap Overpass API.
2. `process_data.py` — geometry validation/repair, duplicate removal, attribute normalisation, building-height estimation from `building:levels` (documented), CRS verification.
3. `load_to_postgis.py` — bulk load processed GeoJSON into PostGIS (Milestone 3).

When public Overpass endpoints are unavailable, use `extract_pbf_data.py` with
a Pakistan `.osm.pbf` extract. It generates the same raw theme files locally.

Run order: download → process → load. Each script is idempotent and re-runnable.
