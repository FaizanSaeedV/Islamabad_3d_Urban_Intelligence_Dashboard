@echo off
setlocal
cd /d "%~dp0"
docker compose down
echo Islamabad Digital Twin stopped. Database data has been preserved.
pause
