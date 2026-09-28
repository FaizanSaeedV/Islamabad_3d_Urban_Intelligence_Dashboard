@echo off
setlocal
cd /d "%~dp0"

echo =====================================================
echo  Islamabad 3D Urban Intelligence Digital Twin
echo =====================================================
echo.

where docker >nul 2>nul
if errorlevel 1 (
  echo Docker Desktop is not installed or is not available in PATH.
  echo Install Docker Desktop, start it, and run this file again.
  echo https://www.docker.com/products/docker-desktop/
  pause
  exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
  echo Docker Desktop is installed but not running.
  echo Start Docker Desktop and run this file again.
  pause
  exit /b 1
)

echo Building the CesiumJS frontend, FastAPI backend and PostGIS database...
docker compose up --build -d
if errorlevel 1 goto :error

echo Waiting for the application to become ready...
timeout /t 12 /nobreak >nul
start "" http://localhost:8080

echo.
echo Application: http://localhost:8080
echo API docs:    http://localhost:8080/docs
echo.
echo To stop it later, run STOP_ISLAMABAD_TWIN.bat
pause
exit /b 0

:error
echo.
echo Startup failed. Run this command to inspect the logs:
echo docker compose logs
pause
exit /b 1
