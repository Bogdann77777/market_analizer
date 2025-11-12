@echo off
REM ============================================================
REM ASHEVILLE LAND ANALYZER - Quick Start
REM ============================================================

title Asheville Land Analyzer

cls
echo.
echo ============================================================
echo    ASHEVILLE LAND ANALYZER
echo ============================================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [!] First time setup needed
    echo.
    echo Running setup...
    call setup.bat
    if errorlevel 1 (
        echo [ERROR] Setup failed
        pause
        exit /b 1
    )
    echo.
    echo Setup complete! Please configure .env file and run START.bat again
    pause
    exit /b 0
)

REM Open menu
call menu.bat

exit /b 0
