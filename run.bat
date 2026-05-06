@echo off
REM Quick launch script for Face Tracking System (Windows)

:menu
cls
echo ======================================================================
echo 🎯 Face Recognition ^& Tracking System
echo ======================================================================
echo.
echo Select mode:
echo 1) GUI Application (Recommended)
echo 2) Command-line Application
echo 3) Enroll New Face
echo 4) Test System
echo 5) Exit
echo.
set /p choice="Enter choice [1-5]: "

if "%choice%"=="1" goto gui
if "%choice%"=="2" goto cli
if "%choice%"=="3" goto enroll
if "%choice%"=="4" goto test
if "%choice%"=="5" goto exit
goto invalid

:gui
echo.
echo 🚀 Launching GUI Application...
python gui_tracker.py
goto end

:cli
echo.
echo 🚀 Launching Command-line Application...
echo    Controls: q=quit, r=reset servos, s=save frame
python main.py
goto end

:enroll
echo.
echo 👤 Face Enrollment
echo.
set /p name="Enter person's name: "
set /p count="Number of images to capture [5]: "
if "%count%"=="" set count=5
python enroll_faces.py --mode camera --name "%name%" --count %count%
goto end

:test
echo.
echo 🧪 Running System Tests...
python test_system.py
goto end

:invalid
echo Invalid choice
pause
goto menu

:exit
echo Goodbye!
exit /b 0

:end
echo.
pause
goto menu
