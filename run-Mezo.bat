@echo off
REM Quick launch script for Face Tracking System (Windows)

:menu
cls
echo ======================================================================
echo Face Recognition ^& Tracking System
echo ======================================================================
echo.
echo Select mode:
echo 1) Launch GUI
echo 2) Exit
echo.
set /p choice="Enter choice [1-2]: "

if "%choice%"=="1" goto gui
if "%choice%"=="2" goto exit
goto invalid

:gui
echo.
echo Launching GUI...
cd desktop
python gui_tracker.py
cd ..
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
