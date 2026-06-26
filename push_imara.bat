@echo off
cd /d "%~dp0"
echo === Imara push: v1.96 Sentry + Langfuse observability ===
echo.
if exist ".git\index.lock" del /f /q ".git\index.lock"
git reset
echo (index rebuilt from HEAD - working-tree changes preserved)
git add backend/services/tracing.py
git add backend/services/obs.py
git add backend/main.py
git add backend/requirements.txt
git add backend/.env.example
git add backend/tests/test_tracing_export.py
git add frontend/package.json
git add frontend/src/main.jsx
git add frontend/vercel.json
git add ECOSYSTEM_FIT_ANALYSIS.md
git add IMARA_IMPROVEMENT_ROADMAP.md
echo.
echo === About to commit (staged below, NO deletions): ===
git status --short
echo.
git commit ^
  -m "feat(obs): wire up Sentry (crash monitoring) + Langfuse (LLM observability) (v1.96)" ^
  -m "Sentry backend hardened (max_request_body_size=never, POPIA-safe; activates on SENTRY_DSN). Frontend @sentry/react conditional init on VITE_SENTRY_DSN + window.Sentry for the v1.89 ErrorBoundary + CSP connect-src to ingest hosts. Langfuse export upgraded to production-grade: singleton client, per-analysis trace grouping via new_ledger(analysis_id), flush in worker finally, pinned v2 API. Privacy by construction - the record_call seam only sees token counts, never prompt text, so no client financials leave to Langfuse. Both no-op until keys set. +6 tracing tests, 465 pytest pass, ruff/vulture clean, vite build clean. Activation (Ruan): SENTRY_DSN + LANGFUSE_* on Railway, VITE_SENTRY_DSN on Vercel."
git push
echo.
echo === Done. Code change deploys; integrations stay dormant until you set the env keys. ===
pause
