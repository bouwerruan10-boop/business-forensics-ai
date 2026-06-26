@echo off
cd /d "%~dp0"
echo === Imara — clear stale .git\index.lock ===
echo.
set "LOCK=.git\index.lock"

if not exist "%LOCK%" (
  echo No lock file present. You're good to run git push.
  goto done
)

echo Found %LOCK%. Attempting a normal delete...
del /f /q "%LOCK%" 2>nul
if not exist "%LOCK%" ( echo Removed. & goto ok )

echo Normal delete failed. Taking ownership and granting rights...
takeown /f "%LOCK%" >nul 2>&1
icacls "%LOCK%" /grant "%USERNAME%":F >nul 2>&1
del /f /q "%LOCK%" 2>nul
if not exist "%LOCK%" ( echo Removed after takeown. & goto ok )

echo.
echo COULD NOT remove the lock automatically.
echo It is probably held open by a running program. Do this:
echo   1. Close VS Code, GitHub Desktop, SourceTree, and any open terminals.
echo   2. Re-run this file (fix_git_lock.bat).
echo   3. If it still fails, right-click this file and "Run as administrator".
goto done

:ok
echo.
echo Lock cleared. Verifying git is healthy...
git status -s >nul 2>&1 && echo Git OK — now run git push. || echo Git still reports an issue — see message above.

:done
echo.
pause
