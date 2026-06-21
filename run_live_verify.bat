@echo off
cd /d "%~dp0backend"
echo === Imara LIVE API verification (runs on YOUR machine, where Anthropic is reachable) ===
echo.
echo Step 1/2: installing the two new deps if missing (structlog, sentry-sdk) + a recent anthropic SDK...
python -m pip install structlog sentry-sdk -q
python -m pip install -U "anthropic>=0.69" -q
echo.
echo Step 2/2: running live_verify.py against the real API (a few cheap calls)...
set MOCK_MODE=false
python live_verify.py
echo.
echo === Done. Copy ALL the output above and paste it back to Claude. ===
pause
