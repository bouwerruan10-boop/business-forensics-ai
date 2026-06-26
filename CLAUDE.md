# CLAUDE.md — Imara Business Intelligence

This file is the authoritative guide to the codebase. Read it fully before touching any file.

---

## What This Is

**Imara** — an AI-powered business intelligence platform for South African SMEs. A client fills in a profile form and uploads business documents (financials, bank statements, tax returns, legal docs, HR records, business plan). Up to 15 Claude API calls run sequentially through a pipeline of specialist agents. The output is a structured JSON report rendered in a React dashboard, with optional PDF export.

**Deployed:**
- Backend → Railway (FastAPI, Docker)
- Frontend → Vercel (React/Vite)
- Repo → GitHub (`bouwerruan10-boop/business-forensics-ai`)

## Operating Model — The WAT Framework (Workflows · Agents · Tools)

Imara is a **WAT system**: probabilistic AI handles reasoning, deterministic code handles execution. That separation is the source of its reliability — it is the same "deterministic-first" DNA enforced in the *Coding Disciplines* and *Extending the engine* sections of the codebase guide (`business-forensics-ai/CLAUDE.md`). Read this as the mental model; the sections that follow are the detail.

**Layer 1 — Workflows (the instructions / SOPs)**
- The analysis "SOP" is the CEO pipeline itself: `agents/ceo_agent.py::run_full_analysis()` defines the ordered phases (1 → 5), required inputs, which agents run, and how outputs assemble into the report dict.
- Process SOPs live as markdown under `docs/plans/`, `docs/runbooks/`, and `IMARA_IMPROVEMENT_ROADMAP.md`. The canonical "how to add an agent or feature" SOP is **Extending the engine — the build pattern** in the codebase guide.
- Written in plain language — the way you'd brief a teammate.

**Layer 2 — Agents (the decision-makers)**
- The Python agents in `backend/agents/` — `ceo_agent.py` orchestrates; `specialist_agents.py` (the 11 `ALL_AGENTS`), `market_research_agent.py`, and `economics_agent.py` reason over computed inputs. They **narrate and prioritise; they never invent a number.**
- **You (Claude Code) are also an agent**, at the development layer: read the relevant SOP, run the right tool/service in the correct order, recover from failures, and ask when inputs are ambiguous — don't do execution by hand.
- Example: to gauge distress, an agent does not estimate it — it reads the value computed by `services/distress_score.py`.

**Layer 3 — Tools (the execution)**
- The deterministic modules in `backend/services/` are the tools: every ratio, score, projection, and threshold is computed here — e.g. `financial_ratios.py`, `distress_score.py`, `simulation.py`, `tax_optimizer.py`, `score_contract.py`, `report_generator.py`. Consistent, unit-testable, fast.
- Operational scripts (`scripts/live_e2e.py`, `run_live_verify.bat`) and `services/` helpers do the API calls, parsing (`file_parser.py`), persistence (`database.py` → SQLite), and rendering (`html_report.py`).
- Secrets live **only** in `backend/.env` (`ANTHROPIC_API_KEY`, `SERPER_API_KEY`, …) — never anywhere else. See *Environment Variables* below.

**Why this matters:** if every step were 90% accurate, five chained LLM steps compound to ~59% success. Push the numbers into deterministic services and the LLM is left doing only what it is good at — interpretation and narration — which is exactly why Imara verifies prose against the computed source (`services/faithfulness.py`, `services/prose_verifier.py`).

### How to Operate

**1. Reach for an existing service first.** Before writing new code, check `backend/services/` and `backend/agents/` — Imara already has tools for ratios, scoring, simulation, tax, benchmarks, and reporting. Only build new when nothing fits.

**2. Learn and adapt when things fail.** On an error: read the full trace, fix the service, re-test. **If a change exercises paid Anthropic/SERPER calls or credits, check with Ruan before re-running** (use `MOCK_MODE=true` for import/logic checks that don't need the API). Capture what you learned (rate limits, quirks, timing) in the relevant SOP under `docs/`.

**3. Keep SOPs current — but don't rewrite them unasked.** When you find a better method or a new constraint, update the workflow/runbook. **Do not create or overwrite SOPs without asking** unless explicitly told to — these are durable instructions, not scratch.

### The Self-Improvement Loop

Every failure hardens the system — this mirrors the *Extending the engine* build pattern:
1. Identify what broke.
2. Fix the tool/service.
3. Verify the fix — pressure-test (None / malformed / hostile / huge / unicode / injection) and lock it with a regression test.
4. Update the SOP with the new approach.
5. Gate on a live A/B (`run_live_verify.bat`) if real Anthropic behaviour changed — `MOCK_MODE` cannot judge it.
6. Move on, more robust than before.

### Artifact Flow — durable vs disposable

- **Deliverables (durable):** the report a client/operator sees — the `Dashboard.jsx` render, the shared link, and the PDF/HTML exports (`report_generator.py`, `html_report.py`). The system of record is SQLite at `backend/data/analyses.db`.
- **In-flight state:** `SharedMemory` (`memory/shared_memory.py`) is the single mutable object threaded through the pipeline — it carries computed values between agents; it is not a saved artifact.
- **Disposable:** scratch and intermediate files belong in the session scratchpad (or regenerable `backend/data/` exports), never committed. Anything regenerable is disposable.

**Bottom line:** you sit between intent (the SOPs and pipeline) and execution (the services). Read the instruction, make the call, run the right tool, recover from errors, and leave the system sharper than you found it. Stay pragmatic. Stay reliable. Keep learning.

---

## Local Dev Commands

```bash
# Backend
cd backend
cp .env.example .env   # add ANTHROPIC_API_KEY
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev            # http://localhost:3000
npm run build

# Quick import check
cd backend && MOCK_MODE=true python -c "from agents.ceo_agent import CEOAgent; print('OK')"
```

No automated tests. Manual check: start both servers, submit the SmartIntake form, confirm analysis completes.

---

## Architecture

```
frontend (React/Vite :3000)
  └─ SmartIntake form → POST /api/analyze (multipart)
  └─ polls GET /api/status/{id} every 2s
  └─ fetches GET /api/report/{id} on completion

backend (FastAPI :8000)
  └─ main.py → spawns background task → CEOAgent.run_full_analysis()
  └─ SharedMemory flows through all agents
  └─ SQLite (backend/data/analyses.db)
  └─ Anthropic API
```

Vite dev server proxies `/api/*` → `http://localhost:8000`. In production set `VITE_API_URL`.

---

## Pipeline — CEOAgent (`agents/ceo_agent.py`)

The entire analysis is one sequential call chain in `run_full_analysis()`:

| Phase | Agent(s) | What it does |
|---|---|---|
| 1 | CEO (business model) | Extracts structure from raw data. **Profile values always win over extracted values.** |
| 1b | MarketResearchAgent | Quick brand/market scan (SERPER API). Populates `market_context_summary` which all Phase 2 agents read. |
| 2 | ALL_AGENTS (11 agents) | Sequential specialist analysis. Each makes 2 Claude calls: `analyze()` + `_parse_findings()`. |
| 2b | MarketDeepDiveAgent | Deep competitor + news + opportunity intelligence. |
| 2c | SATaxAgent | SARS compliance: VAT Act, IT14, EMP201, IRP6, tax clearance. Reads `uploaded_tax_text`, `uploaded_financial_text`, `uploaded_bank_text`. |
| 2d | SALegalAgent | SA corporate law: Companies Act 71/2008, BBBEE 53/2003, POPIA 4/2013, LRA 66/1995, CPA 68/2008, NCA 34/2005, CIPC compliance. Reads `uploaded_legal_text`, `uploaded_hr_text`. |
| 3 | CEO (synthesis) | Cross-agent SCR narrative (Situation→Complication→Resolution), systemic themes. |
| 4 | CEO (scoring) | Penalty-weighted scoring from finding severities. No Claude call. |
| 5 | CEO (report) | Executive summary, roadmap, digital twin params. Assembles full report dict. |

**SATaxAgent and SALegalAgent are NOT in `ALL_AGENTS`** — they run as dedicated phases 2c/2d so they benefit from all prior findings context.

---

## ALL_AGENTS List (`agents/specialist_agents.py`)

Order matters — they run sequentially:
1. FinancialAgent
2. AccountingAgent
3. AuditorAgent
4. OperationsAgent
5. LogisticsAgent
6. SalesAgent
7. MarketingAgent
8. HRAgent
9. ProcurementAgent
10. StrategyAgent
11. LegalRiskAgent

**Adding a new specialist agent:**
1. Create a class in `specialist_agents.py` inheriting `BaseAgent`.
2. Implement `analyze(business_data, memory) → list[AgentFinding]`.
3. Add to `ALL_AGENTS` list. CEO Phase 2 picks it up automatically.
4. For SA-specific agents that need prior findings context: add as a dedicated phase in `ceo_agent.py` instead.

### Extending the engine — the build pattern (read before adding ANY feature or agent)

The engine is **deterministic-first**: the LLM never invents a number. Every new agent or analytical feature follows the same spine:

1. **Compute in code.** Put every figure (ratio, score, projection, threshold) in a pure, unit-testable function under `services/` — no LLM. The agent *reads* these values; it does not produce them.
2. **LLM narrates only.** The `analyze()` call turns the computed numbers into findings/prose. It may interpret and prioritise, but every quantitative claim must trace back to a code-computed value.
3. **Verify the narration.** Cross-check LLM output against the computed source (faithfulness + prose verifiers). A number in the prose that isn't in the computed set is a bug — fail closed, don't ship.
4. **Thread a new output through all three layers** or it's invisible: add field(s) to `SharedMemory` (and `to_context_summary()` if synthesis needs them) → assemble into the report dict in CEO Phase 5 → render a section in `Dashboard.jsx` (and `SharedReport.jsx` for public links).
5. **Honour the contract + gates:** findings obey `FINDING_RULES` (specific ZAR + SA legislation); pressure-test the new code (None/malformed/hostile/huge/unicode/injection) and lock it with a regression test; run the cleanup audit (`ruff`/`vulture`/`jscpd`) before "done"; if it changes real Anthropic behaviour, gate on a live A/B (`run_live_verify.bat`) — MOCK_MODE can't judge it.
6. **Keep the Score contract stable.** New analysis usually ships as an *overlay/panel*, not a change to the Imara Score formula, unless the Score is explicitly being recalibrated against real outcomes.

Worked, already-designed example: `IMARA_ECONOMICS_AGENT_PLAN.md` (a macro→firm sensitivity agent adding a "Macro Resilience" overlay — not a Score change).

---

## SharedMemory (`memory/shared_memory.py`)

The single mutable object passed to every agent. Key field groups:

**Business identity** — `business_name`, `industry`, `annual_revenue`, `headcount`, `currency`, `country`

**SA intake profile** — `entity_type`, `cipc_number`, `vat_registered`, `vat_number`, `tax_year_end`, `years_in_business`, `bbbee_level`, `banking_partner`, `report_audience`

**Document text buckets** — one per zone:
- `uploaded_financial_text` — income statement, balance sheet, management accounts
- `uploaded_bank_text` — bank statements
- `uploaded_tax_text` — VAT201, IT14, EMP201, IRP6, tax clearance
- `uploaded_legal_text` — MOI, shareholder agreements, contracts
- `uploaded_hr_text` — payroll, employment contracts
- `uploaded_plan_text` — business plan

**Specialist agent outputs** — `fraud_risk_level/score`, `credit_score/grade`, `valuation_low/mid/high`, `forecast_base/bull/bear_12m`

**Market intelligence** — `market_visibility_score`, `market_sentiment`, `market_news`, `market_competitors`, `market_context_summary`, `market_search_performed`

**SA Tax outputs** — `sa_tax_risk_score`, `sa_tax_summary`, `sa_vat_status`, `sa_tax_clearance_status`, `sa_tax_performed`

**SA Legal outputs** — `sa_legal_risk_score`, `sa_legal_summary`, `sa_bbbee_analysis`, `sa_cipc_status`, `sa_legal_performed`

**Key rules:**
- `to_context_summary()` returns the compact string injected into CEO synthesis — keep it lean.
- `primary_concern` from the intake form must appear in CEO Phases 1, 3, and 5 prompts.
- `profile values beat extracted values` — `_build_business_model()` never overwrites non-zero profile fields.

---

## AgentFinding Schema

Every finding must have all of these or `_parse_findings()` will reject it:

```python
AgentFinding(
    agent="FinancialAgent",
    category="Cash Flow",
    severity="critical",          # critical | high | medium | low
    title="Negative operating cash flow",
    detail="...",
    financial_impact="R 450 000 annual cash drain",
    recommendation="...",
    roi_estimate="...",
    cost_of_inaction="...",
    benchmark_reference="...",
    quick_win=False,
)
```

`FINDING_RULES` constant in `specialist_agents.py` is injected into every agent system prompt — do not weaken it.

---

## Document Routing (`main.py`)

`file_categories` is a JSON array sent from the frontend matching the `files[]` array index-for-index. Categories: `financial`, `bank`, `tax`, `legal`, `hr`, `business_plan`.

`_run_analysis()` builds `category_texts` dict, then populates the correct `uploaded_*_text` bucket on SharedMemory from each document's extracted text.

---

## Frontend Phase State Machine (`src/App.jsx`)

```
intake → analyzing → done
          ↕               ↕
        admin          shared (hash routing for /report/:id URLs)
```

- **intake**: `SmartIntake.jsx` — single-page form replacing the old BusinessProfile + FileUpload two-step. Has 4 sections: Business Identity, Financial & Tax (incl. BBBEE radio buttons), 6 Document Upload Zones, Context & Focus.
- **analyzing**: `AnalysisProgress.jsx` — polls `/api/status/{id}` every 2s, shows agent progress.
- **done**: `Dashboard.jsx` — full report. Sections: Executive Summary, Health Scores, Quick Wins, All Findings, Roadmap, Credit & Fraud, Valuation & Forecast, Market Intelligence, SA Compliance (conditional), What-If Simulator.
- **admin**: `AdminDashboard.jsx` — lists all analyses, view/delete.
- **shared**: `SharedReport.jsx` — hash-routed `/report/:id` public link view.

---

## Document Upload Zones (`SmartIntake.jsx`)

6 zones, each with per-zone file arrays. At submit, builds parallel `files[]` + `file_categories[]` arrays:

| Zone | Category string | Agent(s) that read it |
|---|---|---|
| Financial Statements | `financial` | FinancialAgent, AccountingAgent, AuditorAgent, SATaxAgent |
| Bank Statements | `bank` | FinancialAgent, SATaxAgent |
| Tax Documents | `tax` | SATaxAgent |
| Legal & Contracts | `legal` | LegalRiskAgent, SALegalAgent |
| HR & Payroll | `hr` | HRAgent, SALegalAgent |
| Business Plan | `business_plan` | StrategyAgent, MarketingAgent |

---

## Key Services

| File | Purpose |
|---|---|
| `services/file_parser.py` | Handles messy Excel/CSV/PDF. Sheet domain detection labels sheets as financial/hr/sales etc. 60-row limit, 20-sheet limit, 30-page PDF limit. |
| `services/benchmark_service.py` | Keyword-scans for industry profile. African country profiles activate as country fallback only. `format_benchmark_context()` builds the prompt block every agent uses. |
| `services/database.py` | SQLite persistence with threading.Lock(). `list_analyses()` excludes `report_json` for performance. |
| `services/report_generator.py` | ReportLab PDF. Charts from `charts.py` embedded as PNG bytes. All chart calls wrapped in try/except. |
| `services/html_report.py` | Self-contained HTML report with inline CSS/JS. |

---

## Environment Variables

| Variable | Where | Required | Purpose |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | `backend/.env` | ✅ | Claude API |
| `MODEL` | `backend/.env` | no | Default: `claude-sonnet-4-6` |
| `MAX_TOKENS` | `backend/.env` | no | Default: `4096` |
| `MOCK_MODE` | shell | no | Set `true` to skip Claude calls (import testing) |
| `SERPER_API_KEY` | `backend/.env` | no | Market research. Gracefully skipped if missing. |
| `RATE_LIMIT` | `backend/.env` | no | Default: `3/hour` |
| `API_SECRET_KEY` | `backend/.env` | no | Optional API key gate on `/api/analyze` |
| `VITE_API_URL` | Vercel env | prod | Backend URL. Empty = Vite proxy (dev only). |

---

## Critical Constraints — Never Break These

1. **Bash heredoc for large Python files.** The Edit tool truncates files on the Windows filesystem mount. Always write large Python files with `cat > file << 'PYEOF' ... PYEOF` and verify with `wc -l`. Never use f-strings in heredoc content — use `.format()`.

2. **Profile values beat extracted values.** `_build_business_model()` never overwrites non-zero profile fields with Claude's extractions.

3. **`primary_concern` flows everywhere.** It must appear in CEO Phases 1, 3, and 5 prompts.

4. **FINDING_RULES stays strict.** Every finding must cite specific ZAR amounts and SA legislation references. Do not soften the rules constant.

5. **SA agents excluded from ALL_AGENTS.** SATaxAgent and SALegalAgent run as phases 2c/2d — not in the Phase 2 loop — so they can read all prior agent findings.

6. **Git operations from user's Windows terminal.** The sandbox cannot read `.git/config`. Use `push_imara.bat` (double-click in File Explorer) for all pushes.

---

## SA Coverage Reference

**Tax (SATaxAgent):** VAT Act 89/1991, Income Tax Act 58/1962 (IT14), EMP201/PAYE/SDL, IRP6 provisional tax, tax clearance certificate, SARS debt management.

**Legal (SALegalAgent):** Companies Act 71/2008, BBBEE Act 53/2003, POPIA Act 4/2013, LRA 66/1995, CPA 68/2008, NCA 34/2005, CIPC compliance, beneficial ownership register.

---

## Coding Disciplines — How To Work In This Repo

These bind every session (they formalise what's already practised here, plus lessons paid for in bugs). The CI ratchet enforces some; the rest are on you.

**The four rules.**
1. **Think before coding.** State assumptions, surface ambiguity, no silent guesses.
2. **Simplicity first.** The minimum code that works. No speculative abstractions or future-proofing not asked for.
3. **Surgical changes.** Touch only what the task requires — no drive-by refactors, renames, or unrequested comments.
4. **Goal-driven.** Define "done" and a verification *before* starting; verify *before* stopping.

**Standing disciplines (Imara-specific).**
- **Cleanup is part of "done."** After every feature, audit + prune the mess it added (dead code, duplication, unused components). Verify each candidate with tools (`ruff`, `vulture`, `jscpd`) before deleting — never on the model's say-so. CI runs `ruff --select F401,F811,F841` as a hard gate + `vulture` advisory.
- **Deterministic-first / anti-hallucination DNA.** Numbers are computed in code; the LLM only narrates. Always verify narration against the computed source (faithfulness + prose verifiers). Do not let an agent invent a figure.
- **Research before building.** Don't add agents, panels, or features for their own sake. The bottleneck is evidence + distribution, not surface area (see `IMARA_IMPROVEMENT_ROADMAP.md`).
- **Pressure-test every change.** Adversarially probe new code (malformed/None/hostile/huge/unicode input, injection) and lock the result with a regression test before considering it done.
- **Don't ship unverified LLM-behaviour changes.** Anything that changes real Anthropic API behaviour can't be judged in the MOCK_MODE sandbox — gate it on a live A/B (`run_live_verify.bat`).

**Paid-in-bugs lessons.**
- `dict.get(key, default)` does **not** return the default when the key exists with a `None` value — coerce numeric/iterable fields with `or 0` / `or []` (v1.31).
- Edit/Write tools silently **truncate** large files on the Windows mount — edit large `.py`/`.md` files with bash heredoc or python string-replace, then `ast.parse` / line-count to verify (Critical Constraint #1).

