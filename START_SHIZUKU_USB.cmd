@echo off
setlocal
title Shizuku - USB startup without Wi-Fi
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Start-ShizukuUsb.ps1"
if errorlevel 1 echo Startup failed. Read the error above.
pause
