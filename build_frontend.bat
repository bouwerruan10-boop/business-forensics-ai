@echo off
cd /d "%~dp0frontend"
echo === npm run build (frontend) ===
echo.
call npm run build
echo.
echo === BUILD EXIT CODE: %errorlevel% ===
pause
