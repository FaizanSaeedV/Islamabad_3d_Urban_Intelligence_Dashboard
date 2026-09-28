# Deployment Guide

Free-tier deployment: **frontend on GitHub Pages, backend + PostGIS on Render**.

## 1. Backend + database on Render

The repository ships a `render.yaml` blueprint (backend web service + managed PostgreSQL).

1. Push the repository to GitHub.
2. On https://render.com → **New → Blueprint** → select the repo. Render creates:
   - `smart-city-api` — Python web service (`uvicorn`, health check on `/api/health`);
   - `smart-city-db` — managed PostgreSQL (free tier).
3. In the Render PostgreSQL dashboard, enable PostGIS:
   ```sql
   CREATE EXTENSION postgis;
   ```
   (Render's Postgres supports PostGIS; run in the built-in psql shell.)
4. Load data from your machine into the remote DB — set the External Database URL values in a temporary shell and run the loader:
   ```bash
   set POSTGRES_HOST=<render-host>
   set POSTGRES_DB=<db>
   set POSTGRES_USER=<user>
   set POSTGRES_PASSWORD=<password>
   cd scripts && python load_to_postgis.py --apply-schema
   ```
5. In the service's **Environment** tab confirm the variables from `render.yaml` (DB credentials are wired automatically from the database resource; set `CORS_ORIGINS` to your GitHub Pages URL, e.g. `https://<you>.github.io`).

Free-tier note: the service sleeps after inactivity; the first request takes ~30–60 s. The frontend's status chip will show *offline* until it wakes.

## 2. Frontend on GitHub Pages

A workflow (`.github/workflows/deploy-pages.yml`) publishes `frontend/` on every push to `main`.

1. Repo **Settings → Pages → Source: GitHub Actions**.
2. Edit `frontend/js/config.js`:
   ```js
   API_BASE_URL: "https://smart-city-api.onrender.com",   // your Render URL
   ```
3. Push to `main` → Pages URL: `https://<you>.github.io/smart-city-digital-twin/`.

## 3. Environment variables (backend)

| Variable | Purpose |
|---|---|
| `POSTGRES_HOST/PORT/DB/USER/PASSWORD` | Database connection (auto-wired by render.yaml) |
| `CORS_ORIGINS` | Comma-separated allowed origins — set to your Pages origin |
| `OPEN_METEO_BASE_URL`, `OSRM_BASE_URL` | External APIs (defaults fine; no keys) |

Never commit `.env`. `frontend/js/config.js` contains only public values (the optional Cesium ion token is a public client token — restrict it to your domain in the ion dashboard).

## 4. Post-deployment checks

1. `https://<api>/api/health` → `"connected": true`.
2. `https://<api>/docs` loads.
3. Pages site: buildings render, weather card fills, no CORS errors in the console (if CORS errors: fix `CORS_ORIGINS`, redeploy).
4. Simulation panel updates (engine ticks server-side every 60 s).
