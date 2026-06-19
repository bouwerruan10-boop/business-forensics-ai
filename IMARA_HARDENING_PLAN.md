# Imara — Hardening & Improvement Plan
_Created 2026-06-19. Grounded in web research (sources at end)._

## Why this plan
This session surfaced a recurring failure mode: a truncated file was committed and
silently broke the Railway deploy (healthcheck failure) for hours, and a PDF helper
(`_wrap_flowables`) was called but never defined — both invisible because there are
no tests and no CI. The improvements below prioritise **preventing that class of
failure** first, then methodology, resilience, and security.

## Research-backed decisions
- **SME scoring** (Financial Innovation; CreditBPO; CFI): credit/bankability models
  rest on leverage, liquidity, profitability, coverage (DSCR > 1.5x = strong), and
  activity, with weights ideally set via AHP/TOPSIS calibration. → Our 8 components
  map cleanly; weights stay as a documented v0 (calibration is a future data exercise),
  but we add a **confidence/completeness** signal so a thin score isn't shown as if complete.
- **CORS** (FastAPI docs; multiple guides): `allow_origins=["*"]` with
  `allow_credentials=True` is rejected by browsers and unsafe. → Explicit, env-driven origins.
- **Rate limiting** (SlowAPI guides): in-memory counters split across workers; fine for
  the current single Railway replica, use Redis when scaling. → Keep SlowAPI, document.
- **Structured outputs** (Anthropic, Nov 2025 beta): strict JSON-schema / tool-use removes
  the brittle "free text then second parse call" pattern and halves cost. → Staged (see below).
- **CI** (GitHub Actions FastAPI guides): ubuntu + setup-python, install, import app,
  compile, plus a Node/Vite build job. → Implemented.

## Implemented now (safe, high-value)
1. **CI smoke-check** — `.github/workflows/ci.yml`: backend job (pip install, `ast` compile
   of every .py, `from main import app`) + frontend job (`npm ci`/`install`, `npm run build`).
   Catches truncation, missing helpers, bad imports, and build breaks before merge.
2. **Version visibility** — `/api/health` returns the deploy commit SHA (from Railway's
   `RAILWAY_GIT_COMMIT_SHA`) so stale deploys are obvious instead of guessed.
3. **Imara Score confidence** — new `imara_confidence` (high/medium/low + % completeness)
   from how many of the 8 components were actually produced; surfaced in API, hero, reports.
4. **Single source of truth for bands** — backend emits `imara_color`; PDF/HTML/React consume
   it (fallback to local map) so the band thresholds/colours can't drift across 4 files.
5. **Pipeline resilience** — each Phase-2 agent (and the market/SA phases) wrapped in
   try/except so one agent failure degrades gracefully instead of failing the whole analysis.
6. **Sub-score robustness** — `_score_business` caps any single agent's penalty contribution
   so one verbose agent can't dominate the health scores.
7. **Security** — env-driven CORS allowlist (default = Vercel domain + localhost), and the
   frontend sends `X-API-Key` when `VITE_API_KEY` is set (backward-compatible; gate already
   exists server-side via `API_SECRET_KEY`).
8. **Bug fix** — `_wrap_flowables` (called but never defined) added; PDF export no longer
   500s on real reports with findings.

## Staged (deliberately not done blind)
- **Structured-output rewrite of all 17 agents** — high value (reliability + ~halved cost)
  but a large change to a live product; should be done agent-by-agent with live eval, not
  in one untested sweep. Recommended next focused workstream.
- **Parallelise Phase-2 agents** — they're independent; async fan-out would cut runtime
  from minutes to seconds. Pairs naturally with the structured-output work.
- **AHP/back-tested weight calibration** for the Imara Score, using real lending outcomes.

## Sources
- Financial Innovation — multicriteria SME credit scoring (BWM/TOPSIS): https://jfin-swufe.springeropen.com/articles/10.1186/s40854-021-00295-5
- CreditBPO — SME credit risk ratios & scoring: https://creditbpo.com/blog/the-ultimate-guide-to-sme-credit-risk-assessment
- Corporate Finance Institute — credit analysis ratios: https://corporatefinanceinstitute.com/resources/commercial-lending/credit-analysis-ratios/
- FastAPI security best practices (CORS/auth): https://blog.greeden.me/en/2025/07/29/fastapi-security-best-practices-from-authentication-authorization-to-cors/
- SlowAPI rate limiting in FastAPI: https://shiladityamajumder.medium.com/using-slowapi-in-fastapi-mastering-rate-limiting-like-a-pro-19044cb6062b
- Anthropic structured outputs guide: https://towardsdatascience.com/hands-on-with-anthropics-new-structured-output-capabilities/
- GitHub Actions CI for FastAPI: https://hasansajedi.medium.com/fastapi-and-github-actions-67d86c1e6c5f
