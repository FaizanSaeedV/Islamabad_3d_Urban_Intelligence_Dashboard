@echo off
REM =====================================================================
REM  Smart City Digital Twin - one-click launcher
REM  Starts the backend API (port 8000) and frontend server (port 5500)
REM  in their own windows, then opens the app in your browser.
REM =====================================================================
cd /d "%~dp0"

start "Digital Twin - Backend API (do not close)" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\activate && uvicorn app.main:app --port 8000"

start "Digital Twin - Frontend (do not close)" cmd /k "cd /d "%~dp0frontend" && py -m http.server 5500"

timeout /t 6 /nobreak >nul
start http://localhost:5500

echo Both servers started in separate windows. Closing this one is safe.
timeout /t 5 >nul
