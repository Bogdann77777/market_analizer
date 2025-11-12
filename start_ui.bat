@echo off
echo ========================================
echo   ASHEVILLE LAND ANALYZER - Web UI
echo ========================================
echo.
echo Starting web server...
echo.
echo Once started, open your browser to:
echo http://localhost:5001
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start Flask web server
python src\web\app.py

pause
