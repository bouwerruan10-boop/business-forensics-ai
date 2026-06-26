@echo off
cd /d "%~dp0"
echo === Imara: re-trigger Railway + Vercel deploy of the latest main ===
echo.
echo This pushes a tiny EMPTY commit to re-fire the GitHub deploy webhooks.
echo No code changes - it just nudges Railway + Vercel to build the latest main.
echo.
if exist ".git\index.lock" del /f /q ".git\index.lock"
git commit --allow-empty -m "chore: re-trigger Railway/Vercel deploy of latest main"
git push
echo.
echo === Done. Now watch the Railway + Vercel dashboards for a NEW deployment building. ===
pause
