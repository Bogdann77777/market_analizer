@echo off
REM ============================================================
REM ASHEVILLE LAND ANALYZER - Management Menu
REM ============================================================

:menu
cls
echo.
echo ============================================================
echo    ASHEVILLE LAND ANALYZER - Management Menu
echo ============================================================
echo.
echo [1] Import MLS Data (CSV)
echo [2] Update Street Colors Analysis
echo [3] Generate Interactive Map
echo [4] Check Email for Opportunities
echo [5] Start Telegram Bot
echo [6] Run Full Pipeline
echo [7] Show Database Stats
echo [8] Start Web UI (Local Access Only)
echo [9] Share Access Online (Local + Public Tunnel)
echo [0] Exit
echo.
echo ============================================================
echo.

set /p choice="Select option (0-9): "

if "%choice%"=="1" goto import_data
if "%choice%"=="2" goto update_streets
if "%choice%"=="3" goto generate_map
if "%choice%"=="4" goto check_email
if "%choice%"=="5" goto start_bot
if "%choice%"=="6" goto full_pipeline
if "%choice%"=="7" goto stats
if "%choice%"=="8" goto start_ui
if "%choice%"=="9" goto share_access
if "%choice%"=="0" goto exit

echo.
echo [ERROR] Invalid choice. Please select 0-9.
timeout /t 2 >nul
goto menu

:import_data
cls
echo.
echo ============================================================
echo    IMPORT MLS DATA
echo ============================================================
echo.
set /p csvfile="Enter CSV file path: "

if "%csvfile%"=="" (
    echo [ERROR] No file specified
    pause
    goto menu
)

if not exist "%csvfile%" (
    echo [ERROR] File not found: %csvfile%
    pause
    goto menu
)

echo.
echo Importing: %csvfile%
echo.
call venv\Scripts\activate.bat
python src\scripts\import_mls_data.py "%csvfile%"
echo.
pause
goto menu

:update_streets
cls
echo.
echo ============================================================
echo    UPDATE STREET COLORS ANALYSIS
echo ============================================================
echo.
call venv\Scripts\activate.bat
python src\scripts\update_street_colors.py
echo.
pause
goto menu

:generate_map
cls
echo.
echo ============================================================
echo    GENERATE INTERACTIVE MAP
echo ============================================================
echo.
call venv\Scripts\activate.bat
python -c "from src.map.generator import generate_full_map; generate_full_map()"
echo.
if exist "output\asheville_land_map.html" (
    echo [SUCCESS] Map generated!
    echo Opening map in browser...
    start output\asheville_land_map.html
)
echo.
pause
goto menu

:check_email
cls
echo.
echo ============================================================
echo    CHECK EMAIL FOR OPPORTUNITIES
echo ============================================================
echo.
set /p chatid="Enter Telegram Chat ID (or press ENTER to skip notifications): "

call venv\Scripts\activate.bat
if "%chatid%"=="" (
    python src\scripts\check_email.py
) else (
    python src\scripts\check_email.py --telegram-chat-id %chatid%
)
echo.
pause
goto menu

:start_bot
cls
echo.
echo ============================================================
echo    START TELEGRAM BOT
echo ============================================================
echo.
echo Starting Telegram Bot in new window...
call venv\Scripts\activate.bat
start "Telegram Bot" cmd /c "call venv\Scripts\activate.bat && python src\telegram\bot.py"
echo.
echo [OK] Bot started in background
echo.
pause
goto menu

:full_pipeline
cls
echo.
echo ============================================================
echo    RUN FULL ANALYSIS PIPELINE
echo ============================================================
echo.
echo This will:
echo   1. Update street colors analysis
echo   2. Generate interactive map
echo.
set /p confirm="Continue? (Y/N): "
if /i not "%confirm%"=="Y" goto menu

call venv\Scripts\activate.bat

echo.
echo [1/2] Updating street colors...
python src\scripts\update_street_colors.py

echo.
echo [2/2] Generating map...
python -c "from src.map.generator import generate_full_map; generate_full_map()"

echo.
echo ============================================================
echo [SUCCESS] Full pipeline completed!
echo ============================================================
if exist "output\asheville_land_map.html" (
    echo.
    set /p openmap="Open map in browser? (Y/N): "
    if /i "!openmap!"=="Y" start output\asheville_land_map.html
)
echo.
pause
goto menu

:stats
cls
echo.
echo ============================================================
echo    DATABASE STATISTICS
echo ============================================================
echo.
call venv\Scripts\activate.bat
python -c "from src.data.database import get_session, Property, StreetAnalysis, LandOpportunity, MarketHeatZone; session = get_session(); print(f'Properties: {session.query(Property).count()}'); print(f'Streets Analyzed: {session.query(StreetAnalysis).count()}'); print(f'Land Opportunities: {session.query(LandOpportunity).count()}'); print(f'Market Heat Zones: {session.query(MarketHeatZone).count()}'); session.close()"
echo.
pause
goto menu

:start_ui
cls
echo.
echo ============================================================
echo    START WEB UI (LOCAL ACCESS)
echo ============================================================
echo.
echo Starting web server...
echo.
echo Once started, open your browser to:
echo http://localhost:5001
echo.
echo Press Ctrl+C in the server window to stop
echo ============================================================
echo.
call venv\Scripts\activate.bat
start "Asheville Land Analyzer - Web UI" cmd /c "call venv\Scripts\activate.bat && python src\web\app.py"
echo.
echo [OK] Web UI started in new window
echo.
pause
goto menu

:share_access
cls
echo.
echo ============================================================
echo    SHARE ACCESS ONLINE (WITH YOUR BROTHER)
echo ============================================================
echo.
echo This will create a public URL that anyone can access.
echo.
echo REQUIREMENTS:
echo   - ngrok.exe must be in the project folder
echo   - Download from: https://ngrok.com/download
echo.
echo WHAT HAPPENS:
echo   1. Local server starts
echo   2. Public tunnel creates a URL
echo   3. You copy and share that URL
echo.
set /p confirm="Continue? (Y/N): "
if /i not "%confirm%"=="Y" goto menu

echo.
echo Opening SHARE_ONLINE.bat...
echo.
start "Share Online" cmd /c "SHARE_ONLINE.bat"
echo.
echo [OK] Check the new window for the public URL!
echo.
echo INSTRUCTIONS:
echo   - Look for "Forwarding" line
echo   - Copy the https://....ngrok-free.app URL
echo   - Send it to your brother
echo.
echo [!] Don't close the tunnel window while sharing
echo.
pause
goto menu

:exit
cls
echo.
echo ============================================================
echo    Exiting...
echo ============================================================
echo.
echo Thank you for using Asheville Land Analyzer!
echo.
timeout /t 2 >nul
exit /b 0
