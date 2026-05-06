@echo off
REM Face Tracking System Installation Script for Windows

echo ======================================================================
echo 🚀 Face Recognition ^& Tracking System - Windows Installation
echo ======================================================================
echo.

echo ======================================================================
echo 🐍 Setting Up Python Environment
echo ======================================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.7+ from python.org
    pause
    exit /b 1
)

echo ✅ Python found

REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment already exists
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo ======================================================================
echo 📚 Installing Python Dependencies
echo ======================================================================
echo.
echo This may take 10-20 minutes...
echo.

REM Install dependencies in stages
echo Stage 1/4: Installing NumPy...
pip install numpy==1.24.3

echo Stage 2/4: Installing OpenCV...
pip install opencv-python==4.8.1.78

echo Stage 3/4: Installing MediaPipe (BlazeFace)...
pip install mediapipe==0.10.9

echo Stage 4/4: Installing face_recognition...
pip install face-recognition==1.3.0

REM Install remaining packages
echo Installing remaining packages...
pip install Pillow scipy imutils

REM Optional: Install YOLO
set /p install_yolo="📥 Install YOLOv8 (optional)? (y/N): "
if /i "%install_yolo%"=="y" (
    echo Installing YOLOv8...
    pip install ultralytics==8.1.0
)

echo.
echo ======================================================================
echo 🔧 Setting Up Project
echo ======================================================================

REM Run setup script
python download_models.py

echo.
echo ======================================================================
echo ✅ Installation Complete!
echo ======================================================================
echo.
echo 📋 Next Steps:
echo.
echo 1. Activate virtual environment:
echo    venv\Scripts\activate.bat
echo.
echo 2. Test the system:
echo    python test_system.py
echo.
echo 3. Enroll your face:
echo    python gui_tracker.py
echo    (Select 'Enroll New Face' mode)
echo.
echo 4. Start tracking:
echo    python gui_tracker.py
echo.
echo 📚 Documentation:
echo - Quick Start: QUICK_START.md
echo - Full Guide: README.md
echo.
echo ======================================================================
echo Happy Tracking! 🎯
echo ======================================================================
echo.

pause
