# Imara — Handoff (current) — built to continue in **Claude Code**
_Last updated: 2026-06-26. This supersedes the 2026-06-19 handoff; the older text is preserved in git history and `SESSION_STATE.md`._

---

## 0. First session in Claude Code — do this first
1. **Open Claude Code at the repo root:** `...\Desktop\Claude\Projects\Consulting Firm\business-forensics-ai` (where `.git` lives). Do **not** open a parent "Consulting Firm" folder — there are stale duplicate copies of `CLAUDE.md`/`Dockerfile`/etc. one and two levels up (see §6).
2. **Let Claude Code auto-load `CLAUDE.md`** — it is the authoritative codebase guide (architecture, pipeline, SharedMemory schema, the AgentFinding contract, and the *Critical Constraints — Never Break*). Read it fully before touching code.
3. **Then read, in order:** this `HANDOFF.md` (current state + open work) → `IMARA_IMPROVEMENT_ROADMAP.md` (the canonical living plan) → `docs/MEMORY_EXPORT.md` (long-term project memory carried over from the prior Cowork sessions — Claude Code does **not** inherit it automatically) → `docs/README.md` (the documentation map).
4. **Optional but recommended:** run `/init` only to *review* what Claude Code would generate — **do not overwrite the existing curated `CLAUDE.md`.** Consider adding project-scoped helpers under `.claude/` (commands/agents) later; not required.

**Hard rules that were paid for in bugs (also in CLAUDE.md):** write large `.py`/`.md` files via bash heredoc or Python string-replace — naive editors **truncate** on this Windows mount (this corrupted `specialist_agents.py`, `Dashboard.jsx`, `client.js`); do **git from Windows** via `push_imara.bat` (clears the stale `.git/index.lock`); **profile values beat extracted values**; `primary_concern` must appear in CEO Phases 1/3/5; `SATaxAgent`/`SALegalAgent` stay **out** of `ALL_AGENTS` (they run as phases 2c/2d).

---

## 1. What Imara is
An AI business-intelligence / bankability platform for South African SMEs. A client fills a profile form and uploads documents (financials, bank, tax, legal, HR, business plan); a pipeline of specialist Claude agents (CEO orchestrator + 11 specialists + SA Tax + SA Legal + market research) produces a structured JSON report — headlined by the **Imara Score™** (0–100 bankability) — rendered in a React dashboard with PDF/HTML export. **Deterministic-first DNA:** numbers are computed in code; the LLM only narrates, and narration is checked against the computed figures.

---

## 2. Current live state (2026-06-26)
- **Repo:** GitHub `bouwerruan10-boop/business-forensics-ai`, branch `main`.
- **Deployed commit:** `b981412` (v1.96) is live on `origin/main`. Local `main` is **2 commits ahead, not yet pushed** — `f973513` (the 2026-06-26 documentation reorg) + `bc3104b` (this handoff refresh); both deploy-safe (docs-only — the Dockerfile copies only `backend/`, Vercel builds only `frontend/`). Push with `push_imara.bat` (or `git push`) when ready.
- **Backend** → Railway (FastAPI, Docker, healthcheck `/api/health`). **Frontend** → Vercel (React/Vite), auto-deploys from `main`.
- **Shipped through v1.96 (per carried-over memory — the most current truth; the roadmap doc is dated 21 Jun and lags this):** Imara Score™; deterministic financial-ratios anchor + **faithfulness & prose verifiers** (anti-hallucination); **parallelised Phase-2 pipeline (~11 min, down from ~46)**; full UI overhaul; shareable report links; admin gate; AI-extraction fallback for summary-statement CSVs; **Action Simulator v2** (Monte Carlo); **operator login** (built, dormant until `OPERATOR_PASSWORD` is set); **observability** (Sentry + Langfuse) wired but **dormant until env keys are set**.

---

## 3. Open items — what to do next

### Strategic (Tier 0 — Ruan-led; the real bottleneck is **evidence + distribution**, not more features)
- **Run a founder-led design-partner pilot** — ideally one NBFI/lender (generates labelled approve/repay outcomes fastest) + 1–2 accountants — to collect **≥30–50 real labelled outcomes**. The harness is already built and waiting: `outcomes` table, `services/validation.py` (AUC/Gini/KS), `services/score_calibration.py` (Platt cold-start), `docs/gtm/IMARA_PILOT_PROTOCOL.md`. This is what converts Imara from "engineering-mature" to "evidence-backed."
- **Make the GTM call:** SME-direct via accountants/advisors **vs** white-label underwriting-intelligence for lenders. Decides what gets built next.
- **Trademark clearance on "Imara"** — direct conflict with the established pan-African financial group `imara.com`; possibly the most consequential single item. (See `docs/research/` + `legal/IMARA_TRADEMARK_RISK_BRIEF.md`.)
- **Keep Railway paid** so the backend + persistent volume stay online.

### Operational / buildable (near-term, mostly mine to execute)
- **Activate observability** (you have signed up for Sentry): create 2 Sentry projects → DSNs (Python `imara-backend`, React `imara-frontend`); sign up Langfuse → keys; set `SENTRY_DSN` + `LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST` on **Railway** and `VITE_SENTRY_DSN` on **Vercel**; redeploy + verify. Refs: `docs/research/ECOSYSTEM_FIT_ANALYSIS.md`, `backend/.env.example`. (Langfuse is metadata-only — token counts/model/latency, never prompt text.)
- **Activate operator login:** set `OPERATOR_PASSWORD` on Railway — this gates `/api/report/{id}` and closes the bearer-URL access-control gap.
- **DB durability:** confirm the Railway persistent volume + the scheduled backup/restore (`docs/runbooks/DB_PERSISTENCE_RUNBOOK.md`, `docs/runbooks/BACKUP_RESTORE.md`).
- **Live click-test the Action Simulator v2.**
- **Structured-outputs efficiency** (drop the 2nd parse call; ~40% cost win) — contained change in `base_agent._parse_findings`, **gated on a live A/B** via `run_live_verify.bat`.
- **Deferred housekeeping (from the 2026-06-26 reorg):** dedupe the **outer-folder duplicate copies** and resolve the **orphan repo** at `Desktop\Consulting Firm` (only a bare `.git`). See §6 + the `imara-file-organization` memory.

---

### Build direction chosen 2026-06-26 — new analysis features / agents
Near-term focus is **extending the analysis engine**. Follow `CLAUDE.md → Extending the engine` for the required pattern (compute-in-code → LLM narrates → verify → wire through SharedMemory/report/Dashboard → gates). Candidate work, grounded in what already exists:
- **Macro-economics agent (designed, not built — top candidate).** Macro→single-firm bottom-up sensitivity (rates/FX/inflation/electricity) from free WB + SARB data; IFRS-9 probability-weighted scenarios into the Action Simulator; surfaced as a **"Macro Resilience" overlay, not a Score change**. Full plan: `IMARA_ECONOMICS_AGENT_PLAN.md` (+ `economics-agent-research` memory).
- **Deepen an existing specialist** over adding breadth — e.g. richer working-capital / cash-conversion analytics in FinancialAgent, or a covenant/affordability calculator feeding FundingFit.
- **A new deterministic panel** off data already in SharedMemory (zero new LLM cost) — e.g. a scenario/sensitivity table over the existing figures.
- **Guardrail:** the strategic bottleneck is still **evidence + distribution** (Tier 0). Prefer the feature a design-partner pilot would actually ask for, and keep the Score contract stable.

## 4. Architecture & data-flow (recap — full detail in `CLAUDE.md`)
```
frontend (React/Vite)  SmartIntake form
   └─ POST /api/analyze (multipart: files[] + file_categories[])
   └─ polls GET /api/status/{id}      └─ GET /api/report/{id} on completion
backend (FastAPI)
   └─ main.py routes each document's text into the correct SharedMemory bucket
   └─ CEOAgent.run_full_analysis():
        P1  CEO business model (profile beats extracted)  → P1b Market research
        P2  11 specialists (parallel waves)               → P2b Market deep-dive
        P2c SA Tax   P2d SA Legal (read all prior findings)
        P3  CEO synthesis (SCR)  P4 scoring (Imara Score, no LLM)  P5 report
   └─ SQLite (backend/data/analyses.db) + report JSON
   └─ Anthropic API; deterministic ratios computed in code, verifiers check narration
```

## 5. Run / deploy / test
- **Local:** `cd backend && uvicorn main:app --reload --port 8000`; `cd frontend && npm run dev`. Import smoke check: `cd backend && MOCK_MODE=true python -c "from agents.ceo_agent import CEOAgent; print('OK')"`.
- **Deploy:** `push_imara.bat` (Railway + Vercel auto-deploy from `main`); if Railway misses the webhook, `redeploy_imara.bat` (empty-commit re-trigger). **Verify on the Railway dashboard / a POST / the JS bundle — not cached `/api/health` or `/api/demo` GETs.**
- **Test:** `MOCK_MODE` pytest battery (~324) + `ruff`/`vulture` + `vite build`; live LLM-behaviour changes gated on `run_live_verify.bat`.

## 6. Folder layout & the "two Consulting Firm" gotcha
- **Canonical project = this repo:** `...\business-forensics-ai`. Root holds code (`backend/`, `frontend/`, `scripts/`), build/deploy config, operational `.bat`/`.ps1`, and the entry docs (`CLAUDE.md`, `README.md`, `HANDOFF.md`, `SESSION_STATE.md`, `IMARA_IMPROVEMENT_ROADMAP.md`, `MODEL_CARD.md`, `START.md`). Everything else lives under **`docs/`** (`plans/ research/ audits/ runbooks/ gtm/ prompts/ reports/`) + **`legal/`**. Index: `docs/README.md`.
- **Ignore the duplicates:** the parent folder `...\Consulting Firm\` (a non-repo Cowork folder) and a separate `...\Desktop\Consulting Firm\` (bare `.git` only) contain stale copies. Always work in the repo subfolder. Cleanup of these is the deferred housekeeping item in §3.

## 7. Working disciplines (binding — condensed from `CLAUDE.md` + memory)
Think before coding; simplest thing that works; surgical changes; define "done" + a verification before starting. **Research before building** (the bottleneck is evidence/distribution). **Cleanup is part of "done"** — after every feature, audit + prune dead code/duplication with tools (`ruff`/`vulture`/`jscpd`), verify before deleting (CI ratchet enforces `ruff F401/F811/F841` + vulture advisory). **Deterministic-first / anti-hallucination** — numbers computed in code, narration verified. **Pressure-test** new code (malformed/None/hostile/huge/unicode/injection) and lock with a regression test. **Don't ship unverified LLM-behaviour changes** — gate on a live A/B.
