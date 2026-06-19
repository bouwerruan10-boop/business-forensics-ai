# CLAUDE.md — Imara Business Intelligence

This file is the authoritative guide to the codebase. Read it fully before touching any file.

---

## What This Is

**Imara** — an AI-powered business intelligence platform for South African SMEs. A client fills in a profile form and uploads business documents (financials, bank statements, tax returns, legal docs, HR records, business plan). Up to 15 Claude API calls run sequentially through a pipeline of specialist agents. The output is a structured JSON report rendered in a React dashboard, with optional PDF export.

**Deployed:**
- Backend → Railway (FastAPI, Docker)
- Frontend → Vercel (React/Vite)
- Repo → GitHub (`bouwerruan10-boop/business-forensics-ai`)

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
