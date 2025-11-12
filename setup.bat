@echo off
REM ============================================================
REM ASHEVILLE LAND ANALYZER - Initial Setup
REM ============================================================

echo.
echo ============================================================
echo    ASHEVILLE LAND ANALYZER - Initial Setup
echo ============================================================
echo.

REM Step 1: Check Python
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ from python.org
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found
echo.

REM Step 2: Check/Create venv
echo [2/5] Checking virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)
echo.

REM Step 3: Install dependencies
echo [3/5] Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

REM Step 4: Check .env
echo [4/5] Checking configuration...
if not exist ".env" (
    echo [WARNING] .env file not found
    echo Creating from template...
    copy .env.example .env
    echo.
    echo [IMPORTANT] Please edit .env file and add your configuration:
    echo   - DATABASE_URL (PostgreSQL connection)
    echo   - TELEGRAM_BOT_TOKEN (from @BotFather)
    echo.
    pause
) else (
    echo [OK] .env file found
)
echo.

REM Step 5: Test imports
echo [5/5] Testing imports...
python -c "import sys; sys.path.insert(0, 'src'); from config import CITY_CENTER; print('Imports OK')" 2>nul
if errorlevel 1 (
    echo [WARNING] Some imports failed - check .env configuration
) else (
    echo [OK] Basic imports working
)
echo.

echo ============================================================
echo    SETUP COMPLETE
echo ============================================================
echo.
echo Next steps:
echo   1. Edit .env file with your real configuration
echo   2. Create PostgreSQL database
echo   3. Run: start_server.bat
echo.
echo Press any key to exit...
pause >nul

exit /b 0
