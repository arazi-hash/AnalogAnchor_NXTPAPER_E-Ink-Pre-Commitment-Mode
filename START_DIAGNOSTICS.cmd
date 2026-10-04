@echo off
setlocal
cd /d "%~dp0"
echo NXTPAPER read-only diagnostics
echo This tool checks the USB connection and reads phone identity.
echo It does not change phone modes or settings.
echo.
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3.10 or newer and reopen this window.
    pause
    exit /b 2
)
python "%~dp0nxtpaper_diag.py" --help
echo.
python "%~dp0nxtpaper_diag.py" doctor
echo.
echo See README.md for the next steps and commands.
pause
