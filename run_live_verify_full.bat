@echo off
cd /d "%~dp0backend"
echo === Imara FULL live verification - runs on YOUR machine, real API spend (~15 calls, several minutes) ===
echo.
echo Installing deps if missing (structlog, sentry-sdk, recent anthropic SDK)...
python -m pip install structlog sentry-sdk -q
python -m pip install -U "anthropic>=0.69" -q
echo.
echo Running live_verify.py with FULL=1 (whole /api/analyze pipeline live)...
set MOCK_MODE=false
set FULL=1
python live_verify.py
echo.
echo === Done. Leave this window open - Claude will read the results above. ===
pause
