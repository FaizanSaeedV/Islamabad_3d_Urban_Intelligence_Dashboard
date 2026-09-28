@echo off
REM =====================================================================
REM  Smart City Digital Twin - one-click data pipeline
REM  Downloads OSM data (resumes where it left off), processes it, and
REM  loads it into PostGIS. Database credentials come from .env.
REM  Run by double-clicking, or from a Command Prompt.
REM =====================================================================
setlocal
cd /d "%~dp0"

echo.
echo === Smart City Digital Twin: data pipeline ===
echo (credentials are read from .env; already-downloaded themes are skipped)
echo.

echo [1/4] Activating Python environment...
call backend\.venv\Scripts\activate.bat || goto :error

cd scripts

echo.
echo [2/4] Downloading OpenStreetMap data (resumes automatically)...
python download_osm_data.py || goto :error

echo.
echo [3/4] Processing and validating data...
python process_data.py || goto :error

echo.
echo [4/4] Loading into PostGIS + applying schema + seeding simulation...
python load_to_postgis.py --apply-schema || goto :error

echo.
echo =====================================================
echo  ALL DONE. Refresh http://localhost:5500 in your
echo  browser - 3D buildings and all layers are now live.
echo =====================================================
pause
exit /b 0

:error
echo.
echo *** A step failed - scroll up to see the error message. ***
echo *** Just run this file again: it resumes where it stopped. ***
pause
exit /b 1
