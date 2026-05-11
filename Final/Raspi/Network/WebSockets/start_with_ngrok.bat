@echo off
REM start_with_ngrok.bat
REM Quick start script for Windows testing with Ngrok tunneling

echo ==========================================
echo Raspberry Pi Surveillance System
echo Starting with Ngrok WAN Access (Windows)
echo ==========================================
echo.

REM Check if auth token is set
if "%NGROK_AUTH_TOKEN%"=="" (
    echo WARNING: NGROK_AUTH_TOKEN not set!
    echo.
    echo Please set your Ngrok auth token:
    echo   1. Get token from: https://dashboard.ngrok.com/get-started/your-authtoken
    echo   2. Run: set NGROK_AUTH_TOKEN=your_token_here
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
)

REM Enable Ngrok
set NGROK_ENABLED=true

REM Set default region if not specified
if "%NGROK_REGION%"=="" (
    set NGROK_REGION=us
    echo Using default region: us
    echo To change: set NGROK_REGION=eu (or ap, au, sa, jp, in)
    echo.
)

REM Check Python dependencies
echo Checking dependencies...
python -c "import pyngrok" 2>nul
if errorlevel 1 (
    echo WARNING: pyngrok not installed. Installing...
    pip install pyngrok
)

python -c "import websockets" 2>nul
if errorlevel 1 (
    echo WARNING: websockets not installed. Installing all dependencies...
    pip install -r requirements.txt
)

echo Dependencies OK
echo.

REM Start the system
echo Starting surveillance system...
echo Press Ctrl+C to stop
echo.

python main.py
