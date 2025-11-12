@echo off
cls
color 0A
title Asheville Land Analyzer - Web UI

echo.
echo =========================================================
echo          ASHEVILLE LAND ANALYZER - WEB UI
echo =========================================================
echo.
echo  [1] Starting virtual environment...
call venv\Scripts\activate.bat

echo  [2] Checking dependencies...
python -c "import flask, flask_cors, pandas, sqlalchemy" 2>nul
if errorlevel 1 (
    echo.
    echo  [!] Missing dependencies detected. Installing...
    pip install -q flask flask-cors pandas sqlalchemy
)

echo  [3] Starting web server...
echo.
echo =========================================================
echo   Server Status: RUNNING
echo   URL: http://localhost:5001
echo
echo   Features:
echo   - View properties on map
echo   - Import CSV data (Redfin format)
echo   - Analyze market opportunities
echo   - Filter by urgency and zones
echo =========================================================
echo.
echo  Press [Ctrl+C] to stop the server
echo.

REM Start Flask web server
python src\web\app.py

pause