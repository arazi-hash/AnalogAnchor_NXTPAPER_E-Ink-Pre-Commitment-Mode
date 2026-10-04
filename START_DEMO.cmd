@echo off
setlocal
cd /d "%~dp0"
echo STARTING - five-minute Max Ink demo.
echo Keep the phone connected, unlocked, and in normal mode.
echo Wait for Ready. Then move the slider to Ink.
echo.
where python >nul 2>nul
if errorlevel 1 (
    echo NOT RUNNING - Python 3.10 or newer is required.
    pause
    exit /b 2
)
python -u "%~dp0nxtpaper_demo.py" --once
set "demo_exit_code=%errorlevel%"
echo.
if "%demo_exit_code%"=="0" (
    echo FINISHED - the program has ended.
) else if "%demo_exit_code%"=="130" (
    echo STOPPED - operator stop requested.
) else (
    echo NOT RUNNING - the program stopped with an error.
    echo Read the error above before trying again.
)
echo This window stays open so you can read the messages.
pause
exit /b %demo_exit_code%
