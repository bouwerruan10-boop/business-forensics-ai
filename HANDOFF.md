# Imara — Handoff Document
_Last updated: 2026-06-19_

## Current State (both ends live on commit acf49b6 + this hardening pass staged)
- **Frontend**: Vercel (`business-forensics-ai.vercel.app`) — auto-deploys from GitHub `main`.
- **Backend**: Railway service `web` in project `strong-creativity` — auto-deploys from `main`,
  Dockerfile build, healthcheck `/api/health`. **Account is on a LIMITED TRIAL (~$4.97 / 30 days)
  — the service is suspended when it lapses. Add a plan to keep it online.**

## Shipped this session
### A. Imara Score™ (composite hero metric)
Weighted 0–100 bankability/investability score from all agent outputs, re-normalised over the
components actually produced. `_calculate_imara_score` runs in CEO Phase 4. Fields on SharedMemory
and the report dict: `imara_score`, `imara_band`, `imara_label`, `imara_color`,
`imara_completeness`, `imara_confidence`, `imara_components`. Rendered as a hero in the dashboard,
shared report, PDF (all 3 audiences), and HTML.

### B. CRITICAL repair — `specialist_agents.py`
A prior Edit-tool truncation had committed a broken file (HEAD `81dfa01`) that **failed the Railway
healthcheck** and kept the old build live. Four agent classes were missing; all reconstructed
(`FraudDetectionAgent`, `CreditReadinessAgent`, `ValuationAgent`, `ForecastAgent`) with SA-specific
prompts. The repair commit (`acf49b6`) passed the healthcheck and is live.

### C. Hardening pass (this commit)
1. **CI** — `.github/workflows/ci.yml`: backend (install, compileall, import app, **pytest**) +
   frontend (`npm run build`). Catches truncation/missing-helper/import/build breakage pre-merge.
2. **Tests** — `backend/tests/test_hardening.py` (11 tests, no API key): Imara scoring + confidence,
   sub-score cap, the 4 agents' JSON extraction + fallback, app boot.
3. **Imara confidence** — `imara_confidence` + `imara_completeness` so a thin score (few components)
   isn't shown as solid as a complete one. Single source of truth: backend emits `imara_color`;
   PDF/HTML/React consume it.
4. **Pipeline resilience** — every agent phase wrapped in try/except (one agent failing no longer
   sinks the analysis).
5. **Sub-score robustness** — per-category penalty capped so finding VOLUME can't collapse scores.
6. **Security** — CORS restricted from `*` to the Vercel domain + `*.vercel.app` + localhost
   (env `CORS_ORIGINS`); frontend sends `X-API-Key` when `VITE_API_KEY` set.
7. **Version visibility** — `/api/health` returns the deploy commit (`RAILWAY_GIT_COMMIT_SHA`).

### D. Grounded financial ratios (this commit)
`services/financial_ratios.py` — pure-Python extractor + ratio calculator. Computes margins,
liquidity, gearing, working-capital days, and interest cover **directly from the uploaded
financials (arithmetic, not LLM-generated)**, each metric traceable to its source figures.
A deterministic `financial_fundamentals_score` now **anchors the Imara Score's Profitability
component** (60/40 blend) so the headline number reflects real margins, not finding-count.
Rendered as a "Financial Fundamentals" panel in the dashboard, PDF, and HTML. Fully unit-tested
(6 new tests, no API). Addresses the #1 product risk for a credit tool: number hallucination.

### Two pre-existing bugs fixed
- `_wrap_flowables` was **called but never defined** → PDF export 500'd on any report with findings. Added.
- `client.js` used a relative `/api` that Vercel's SPA rewrite swallowed and **never read
  `VITE_API_URL`** → real analyses through the deployed frontend couldn't reach the backend.
  Now wired to `VITE_API_URL` (this is why the CORS change was needed).

## New / relevant environment variables
| Variable | Where | Purpose |
|---|---|---|
| `CORS_ORIGINS` | Railway (optional) | Comma-separated allowed origins. Default covers Vercel + localhost. |
| `API_SECRET_KEY` | Railway (optional) | Enable the `/api/analyze` key gate. |
| `VITE_API_KEY` | Vercel (optional) | If set, frontend sends `X-API-Key`. Pair with `API_SECRET_KEY`. |
| `VITE_API_URL` | Vercel (prod) | Railway backend URL. Now actually used by the client. |
| `RAILWAY_GIT_COMMIT_SHA` | Railway (auto) | Surfaced in `/api/health`. |

## Staged next (deliberately NOT done blind — see IMARA_HARDENING_PLAN.md)
1. Rewrite all 17 agents to Anthropic strict **structured outputs** (Nov 2025) — kills the brittle
   two-call free-text+reparse, ~halves cost. Do agent-by-agent with live eval.
2. **Parallelise** Phase-2 agents (independent) — minutes → seconds.
3. **AHP / back-tested calibration** of the Imara Score weights against real lending outcomes.

## Critical Rules (Never Break)
1. **Write large files via bash heredoc**, not the Edit/Write tools — they truncate on this Windows
   mount. This corrupted `specialist_agents.py` AND `Dashboard.jsx` AND `client.js` this project.
   The CI smoke-check now catches it, but prevention beats detection. Prefer Python string-replace
   patching for surgical backend edits.
2. **Git writes from Windows** via `push_imara.bat` (clears the stale sandbox lock first).
3. Profile values beat extracted values in `_build_business_model()`.
4. SATaxAgent / SALegalAgent stay out of `ALL_AGENTS` (phases 2c/2d).
5. `primary_concern` must appear in CEO Phases 1, 3, 5.
6. Imara agent `name` strings must match the sets in `_score_business()`.
