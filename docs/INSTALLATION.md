# Installation Guide (Local Development)

Tested on Windows 10/11; Linux/macOS commands noted where they differ.

## Prerequisites

| Software | Version | Notes |
|---|---|---|
| Python | 3.11+ | python.org (tick "Add to PATH") |
| PostgreSQL | 15+ | EDB installer; include **Stack Builder** |
| PostGIS | 3.4+ | via Stack Builder → Spatial Extensions |
| Node.js | 18+ (optional) | only for frontend logic tests |
| Git | any | |

No API keys are required. A free Cesium ion token is *optional* (better terrain).

## 1. Clone & environment

```bash
git clone https://github.com/<you>/smart-city-digital-twin.git
cd smart-city-digital-twin
copy .env.example .env        # Linux/macOS: cp .env.example .env
```

Edit `.env`: set `POSTGRES_PASSWORD` to the password you chose during PostgreSQL installation.

## 2. Python environment

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

## 3. Database

```bash
# Windows: use "SQL Shell (psql)" from the Start Menu, or add
# C:\Program Files\PostgreSQL\15\bin to PATH
psql -U postgres -f database/schema/00_create_database.sql
```

## 4. Data pipeline (10–20 min, needs internet)

```bash
cd scripts
python download_osm_data.py     # 16 themes from Overpass API
python process_data.py          # validate, clean, estimate heights
python load_to_postgis.py --apply-schema   # schema + load + simulation seed
cd ..
```

Expected: per-theme feature counts, then a database summary table. Verify:

```sql
psql -U postgres -d smart_city_twin -c "SELECT count(*) FROM buildings;"
```

## 5. Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Check http://localhost:8000/api/health → `"connected": true` with a PostGIS version, and http://localhost:8000/docs for interactive API docs.

## 6. Frontend

```bash
# new terminal
cd frontend
python -m http.server 5500
```

Open http://localhost:5500 — the camera flies to Islamabad, buildings load, and the API chip shows **online**.

**Optional – better terrain:** create a free account at https://ion.cesium.com, copy your default access token into `CESIUM_ION_TOKEN` in `frontend/js/config.js`.

## 7. Tests

```bash
python -m pytest                       # 40 passed expected with DB loaded
node tests/frontend/logic_tests.mjs    # 12 checks
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `API: online (no DB)` chip | PostgreSQL not running or wrong password in `.env` |
| `psql` not found | Add PostgreSQL `bin` directory to PATH |
| Overpass timeouts | Re-run the script; it rotates across three mirrors — or try later |
| Port in use | Change `--port` and update `CORS_ORIGINS` in `.env` + `API_BASE_URL` in `frontend/js/config.js` |
| Routing/weather 502 | Corporate proxy or offline — data layers still work |
