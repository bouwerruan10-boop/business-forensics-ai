@echo off
title BFA Backend Check
echo ================================================
echo  Checking port 8000 status...
echo ================================================
netstat -ano | findstr :8000
echo.
echo ================================================
echo  Checking if Python is available...
echo ================================================
py --version
echo.
echo ================================================
echo  Starting BFA Backend...
echo ================================================
cd /d "%~dp0backend"
echo Current directory: %CD%
echo.
echo Installing packages...
py -m pip install -r requirements.txt --upgrade
echo.
echo Starting uvicorn...
py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
