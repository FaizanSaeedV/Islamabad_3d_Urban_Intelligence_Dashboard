@echo off
REM =====================================================================
REM  Smart City Digital Twin - git repository initialisation
REM  Creates the repo with a clean milestone-style commit history.
REM  Safe to run once; refuses to run if a repo already exists.
REM =====================================================================
setlocal
cd /d "%~dp0"

if exist ".git" (
    echo A git repository already exists here - nothing to do.
    pause
    exit /b 0
)

git init -b main || goto :error
git config user.name "Diluxan Logeswaran"
git config user.email "diluxanlogeswaran20011210@gmail.com"

echo.
echo [1/8] Scaffolding...
git add .gitignore .env.example LICENSE pytest.ini
git commit -m "chore: project scaffolding - environment template, license, test config" || goto :error

echo [2/8] Data pipeline...
git add scripts/ data/README.md data/raw/.gitkeep data/processed/.gitkeep data/tiles/.gitkeep
git commit -m "feat: OSM data pipeline - Overpass download (16 themes) with mirror failover and resume, validation, height estimation, EPSG:5235 metrics" || goto :error

echo [3/8] Database...
git add database/
git commit -m "feat: PostGIS schema - constrained spatial tables, typed facility views, simulation tables with enforced disclaimers, GIST indexes, analysis queries" || goto :error

echo [4/8] Backend...
git add backend/
git commit -m "feat: FastAPI backend - GeoJSON layers, nearest/route/coverage analysis, grid analytics, Open-Meteo weather, simulation engine, clean error contract" || goto :error

echo [5/8] Frontend...
git add frontend/
git commit -m "feat: CesiumJS frontend - 62k extruded buildings, 16-layer control, emergency response, dashboard, digital twin overlays, CZML time animation, measurement and query tools" || goto :error

echo [6/8] Tests...
git add tests/
git commit -m "test: backend contract/validation suites, pipeline fixture tests, CRS correctness, live spatial validation, frontend logic tests, manual checklist" || goto :error

echo [7/8] Documentation...
git add docs/ README.md
git commit -m "docs: complete documentation set - GIS methodology, architecture, database ER, API reference, user/developer guides, limitations, screenshots" || goto :error

echo [8/8] Deployment + helpers...
git add .
git commit -m "chore: deployment blueprints (Render, GitHub Pages), CI workflows, one-click setup and launcher scripts" || goto :error

echo.
echo ================= Commit history =================
git log --oneline
echo ==================================================
echo.
echo Repository ready. Next: publish with GitHub Desktop
echo (File - Add local repository - this folder - Publish).
pause
exit /b 0

:error
echo *** git step failed - see message above. ***
pause
exit /b 1
