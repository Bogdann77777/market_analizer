@echo off
cls
color 0A
title Share Your Land Analyzer Online

echo.
echo ============================================================
echo       SHARE YOUR LAND ANALYZER - SIMPLE VERSION
echo ============================================================
echo.
echo This will make your Land Analyzer accessible from anywhere!
echo.
echo ============================================================
echo                   HOW IT WORKS:
echo ============================================================
echo.
echo 1. We start your local server (Flask)
echo 2. We use NGROK to create a public URL
echo 3. You share that URL with your brother
echo 4. He can access your map from his computer
echo.
echo ============================================================
echo                  FIRST TIME SETUP:
echo ============================================================
echo.
echo If you DON'T have ngrok yet:
echo.
echo   1. Go to: https://ngrok.com/download
echo   2. Click "Download for Windows"
echo   3. Extract ngrok.exe to THIS folder:
echo      E:\market_analyzer\
echo   4. That's it! No registration needed for basic use
echo.
echo ============================================================
echo.

REM Check if ngrok exists
if not exist ngrok.exe (
    echo [ERROR] ngrok.exe not found in current folder!
    echo.
    echo Please download ngrok and put ngrok.exe here:
    echo %cd%
    echo.
    echo Download from: https://ngrok.com/download
    echo.
    set /p open="Open download page now? (Y/N): "
    if /i "!open!"=="Y" start https://ngrok.com/download
    echo.
    pause
    exit
)

echo [OK] ngrok.exe found!
echo.
echo ============================================================
echo              STARTING YOUR SERVICES...
echo ============================================================
echo.

REM Start Flask server
echo [1/2] Starting Flask server...
call venv\Scripts\activate.bat
start /B cmd /c "python src\web\app.py > nul 2>&1"

echo      Waiting for server to start...
timeout /t 5 /nobreak >nul
echo      [OK] Server running on http://localhost:5001
echo.

REM Start ngrok
echo [2/2] Creating public tunnel with ngrok...
echo.
echo ============================================================
echo.
echo   YOUR PUBLIC URL WILL APPEAR BELOW:
echo.
echo   Look for a line that says:
echo   "Forwarding" followed by a URL like:
echo   https://1234-56-78-90-123.ngrok-free.app
echo.
echo   COPY THAT URL and send it to your brother!
echo.
echo ============================================================
echo.

ngrok.exe http 5001

echo.
echo ============================================================
echo   Tunnel stopped.
echo ============================================================
pause
