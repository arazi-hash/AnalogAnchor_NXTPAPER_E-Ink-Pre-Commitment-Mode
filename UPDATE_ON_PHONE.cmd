@echo off
setlocal
title NXTPAPER Guard - Install updated APK
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Install-Guard.ps1"
if errorlevel 1 echo Installation failed. Read the error above.
pause
