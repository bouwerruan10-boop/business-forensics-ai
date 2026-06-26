@echo off
title Install Imara desktop app
echo Creating the Imara desktop app shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_imara_shortcut.ps1"
echo.
echo You can now launch "Imara" from your Desktop.
echo.
pause
