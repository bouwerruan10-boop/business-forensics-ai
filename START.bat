@echo off
title Business Forensics AI — Startup
echo ================================================
echo  Business Forensics AI Platform
echo ================================================
echo.

:: ── Backend ──────────────────────────────────────
echo [1/2] Starting backend on http://localhost:8000 ...
cd /d "%~dp0backend"

:: Install deps quietly if needed
py -m pip install -r requirements.txt --upgrade -q 2>nul

:: Start uvicorn in a new window
start "BFA Backend" cmd /k "py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for it to boot
timeout /t 4 /nobreak >nul

:: ── Frontend ─────────────────────────────────────
echo [2/2] Starting frontend on http://localhost:3000 ...
cd /d "%~dp0frontend"

:: Install node modules if needed
if not exist node_modules (
    echo Installing npm packages — this may take a minute...
    npm install
)

:: Start Vite dev server in a new window
start "BFA Frontend" cmd /k "npm run dev"

:: Wait a moment then open browser
timeout /t 3 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo ================================================
echo  Both servers are starting.
echo  The app will open in your browser shortly.
echo  Close the two CMD windows to stop the servers.
echo ================================================
