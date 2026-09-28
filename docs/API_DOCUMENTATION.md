# API Documentation

Base URL (local): `http://localhost:8000`. Interactive OpenAPI docs at **`/docs`** (Swagger) and `/redoc`. All endpoints are `GET`; responses are JSON; GeoJSON follows RFC 7946 (EPSG:4326).

## Error contract

| Status | Meaning |
|---|---|
| 422 | Invalid input (message explains the parameter) |
| 502 | Upstream service (OSRM / Open-Meteo) unavailable |
| 503 | Database unavailable |

## Health

- `GET /` — service metadata.
- `GET /api/health` — `{status, version, database:{connected, postgis_version}}`.

## Layers (GeoJSON FeatureCollections)

Common params: `bbox=west,south,east,north` · `limit` · `simplify_m` (metric simplification tolerance).

- `GET /api/buildings` — props: `name, building_type, levels, height_m, height_source, amenity, footprint_area_m2`
- `GET /api/roads` · `/api/railways` · `/api/waterways` · `/api/water-bodies` · `/api/landuse` · `/api/green-spaces`
- `GET /api/facilities?type=` — 9 types: `hospital, police_station, fire_station, school, fuel_station, ev_charging, bus_stop, parking, railway_station`
- Aliases: `GET /api/hospitals`, `/api/fuel-stations`, `/api/ev-stations`, `/api/parking`

## Mobility & analysis

- `GET /api/nearest?lon&lat&type&n` — K nearest facilities; KNN + exact geodesic re-ranking; results distance-sorted.
- `GET /api/route?from_lon&from_lat&to_lon&to_lat` — OSRM route: `distance_m, duration_s (free-flow), straight_line_m, geometry` (LineString).
- `GET /api/coverage?type&radius_m&include_geometry` — EPSG:32643 dissolved buffers vs building centroids: counts, `underserved_pct`, simplified `service_area`.

## Analytics

- `GET /api/analytics` — `totals` + five Chart.js-ready datasets (`{labels, values}`), height-classification note.

## Advanced analysis

- `GET /api/analysis/green-space?lon&lat&radius_m` — nearest green space (name, geodesic m), count + hectares within radius.
- `GET /api/analysis/green-access-grid?cell_m` — GeoJSON choropleth; `distance_m` per metric cell; method in `metadata`.
- `GET /api/analysis/building-density?cell_m` — `count` + `avg_height_m` per metric cell.

## Spatial query

- `GET /api/query/buildings-near-facility?type&radius_m&limit`
- `GET /api/query/facilities-within?lon&lat&radius_m&type(optional)`
- `GET /api/query/facilities-near-roads?type&radius_m` — major roads = motorway/trunk/primary/secondary.

## Weather

- `GET /api/weather` — current Islamabad conditions (Open-Meteo, 5-min server cache): `temperature_c, humidity_pct, precipitation_mm, rain_mm, cloud_cover_pct, wind_speed_kmh, wind_direction_deg, weather_code (WMO), is_day, fetched_at`.

## Digital twin simulation

- `GET /api/simulation/status` — `{disclaimer, is_simulated: true, traffic[], parking[], ev_chargers[]}`. **All values are simulated for demonstration** — the disclaimer ships in every response and the database enforces `is_simulated = TRUE`.

## Validation windows

Coordinates: lon 70.0–75.5, lat 31.0–36.5 (Pakistan window). Radii: 10–10 000 m (queries), 100–10 000 m (coverage/green). Grid cells: 100–1000 m. Limits: per-endpoint caps documented in `/docs`.
