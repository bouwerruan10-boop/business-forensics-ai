# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Business Forensics AI — a solo consulting tool. A client uploads Excel/CSV/PDF business data, 11 specialist Claude agents run sequentially, and the platform outputs a McKinsey-quality PDF report with quantified findings, scores, and a 90-day implementation roadmap.

---

## Commands

### Backend

```bash
cd backend
cp .env.example .env          # first-time setup — add ANTHROPIC_API_KEY
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                   # dev server on http://localhost:3000
npm run build                 # production build → dist/
```

There are no automated tests. Manual verification: start both servers, upload a sample Excel file, wait for the analysis pipeline to complete (~3–8 min), and confirm the PDF downloads.

---

## Architecture

```
frontend (React/Vite :3000)  ──→  backend (FastAPI :8000)  ──→  Anthropic API
                                        │
                                   SQLite (backend/data/analyses.db)
```

The Vite dev server proxies `/api/*` to `http://localhost:8000` (see `vite.config.js`). In production set `VITE_API_URL` in the frontend environment and the proxy is bypassed.

---

## Backend Deep Dive

### Pipeline Flow (`agents/ceo_agent.py → CEOAgent.run_full_analysis`)

This is the core of the system — all 13 Claude API calls per analysis flow through here:

1. **Phase 1 — Business model extraction**: CEO Agent calls Claude to extract structure from raw data. Profile values (revenue, headcount, currency) provided by the user always win over extracted values.
2. **Phase 2 — 11 specialist agents** run sequentially from `ALL_AGENTS` list in `agents/specialist_agents.py`. Each agent calls `_call_claude()` for domain analysis, then calls `_call_claude()` a second time inside `_parse_findings()` to convert prose into structured `AgentFinding` objects.
3. **Phase 3 — Cross-agent synthesis**: CEO Agent calls Claude with all findings to produce the McKinsey SCR narrative (Situation → Complication → Resolution), systemic themes, and ranked priority issues.
4. **Phase 4 — Scoring**: penalty-weighted scoring from finding severities. No Claude call.
5. **Phase 5 — Report assembly**: CEO Agent calls Claude for executive summary, roadmap, and digital twin parameters, then assembles the full report dict.

### SharedMemory (`memory/shared_memory.py`)

The single mutable context object passed to every agent. Key things to know:
- `to_context_summary()` returns compact JSON injected into every agent prompt — keep it lean.
- `primary_concern` (from the profile form) must be threaded through CEO Agent prompts — it gates what the executive summary opens with.
- Scores are set directly on the memory object by `_score_business()`, not by individual agents.

### AgentFinding (`memory/shared_memory.py`)

Every finding must have: `severity` (critical/high/medium/low), `financial_impact`, `recommendation`, `roi_estimate`, `cost_of_inaction`, `benchmark_reference`, `quick_win` (bool). The `_parse_findings()` method in `BaseAgent` enforces this schema via a second Claude call.

### Adding a New Specialist Agent

1. Create a class in `agents/specialist_agents.py` inheriting `BaseAgent`.
2. Set `name`, `system_prompt` (include `FINDING_RULES`), and implement `analyze(business_data, memory)`.
3. Add it to the `ALL_AGENTS` list at the bottom of that file.
4. CEO Agent's Phase 2 loop picks it up automatically.

### Benchmark System (`services/benchmark_service.py` + `data/benchmarks.json`)

- `detect_industry()` keyword-scans business name, industry hint, and file names against benchmark profiles. African country profiles (`south_africa_sme`, `nigeria_general`, `kenya_general`, `zimbabwe_general`) are excluded from keyword scan — they activate only as a country fallback when no specific industry matches.
- `format_benchmark_context()` builds the prompt block injected into every agent. If `african_context` key exists in a profile, it appends an "AFRICAN MARKET CONTEXT" block.
- To add a new industry: add an entry to `data/benchmarks.json` under `industries`, then add keywords.

### File Parser (`services/file_parser.py`)

Handles messy real-world files. Key behaviours:
- Excel: re-reads with `header=1` if the first row looks like a title row (≤2 non-null values). Deduplicates column names, coerces object columns to numeric/date when >60% of values parse successfully.
- CSV: tries encodings in order: utf-8 → utf-8-sig → latin-1 → cp1252.
- Sheet domain detection (`_detect_domain`) labels sheets as `financial`, `hr`, `sales`, etc. — this is what populates `business_data['financial']`, `business_data['hr']`, etc. that specialist agents receive.
- Limits: 60 sample rows, 20 sheets, 30 PDF pages.

### Persistence (`services/database.py`)

SQLite at `backend/data/analyses.db`. All functions use a module-level `threading.Lock()` because FastAPI runs background tasks in a thread pool. The full `report_json` blob is only fetched by `get_report()` — `list_analyses()` excludes it for performance.

### Rate Limiting & API Key Gate (`main.py`)

- `RATE_LIMIT` env var (default `3/hour`) controls slowapi rate limiting on `POST /api/analyze`.
- `API_SECRET_KEY` env var: if set, all `/api/analyze` calls require `X-API-Key` header matching this value. Leave blank to disable.

### PDF Generation (`services/report_generator.py`)

ReportLab-based. Charts from `services/charts.py` are embedded as PNG bytes via `io.BytesIO`. All chart calls are wrapped in `try/except` — chart failures are silently skipped, never crash the PDF.

**Critical**: This file and any other Python files with f-strings containing complex expressions are vulnerable to truncation when edited with file-editing tools. **Always rewrite large Python files using bash heredoc** (`cat > file << 'PYEOF' ... PYEOF`) and verify with `python3 -c "import ast; ast.parse(open('file.py').read())"`. Never use f-strings in files written this way — use `.format()` instead.

---

## Frontend Deep Dive

### Phase State Machine (`src/App.jsx`)

`phase` state drives the entire UI: `profile → upload → analyzing → done | admin`.

- `profile`: `BusinessProfile.jsx` collects company name, industry, revenue, headcount, currency, country, primary concern.
- `upload`: `FileUpload.jsx` drag-and-drop. On submit calls `POST /api/analyze` with multipart form data.
- `analyzing`: polls `GET /api/status/{id}` every 2 seconds. `AgentActivity.jsx` displays live agent progress.
- `done`: `Dashboard.jsx` renders the full report with tabs (Executive Summary, Findings, Roadmap, Digital Twin).
- `admin`: `AdminDashboard.jsx` fetches `GET /api/admin/analyses`, shows all analyses, supports delete and jump-to-report.

### API Client (`src/api/client.js`)

All backend calls go through this file. `VITE_API_URL` env var overrides the base URL (falls back to empty string, which uses the Vite proxy in dev).

### Scores Display

`ScoreCards.jsx` renders the four health scores (business_health, profitability, efficiency, risk) as recharts `RadialBarChart` components. Score values come from `report.scores`.

---

## Environment Variables

| Variable | Where | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | `backend/.env` | **Required.** Claude API key. |
| `MODEL` | `backend/.env` | Claude model. Default: `claude-sonnet-4-6` |
| `MAX_TOKENS` | `backend/.env` | Max tokens per agent call. Default: `4096` |
| `RATE_LIMIT` | `backend/.env` | slowapi rate limit string. Default: `3/hour` |
| `API_SECRET_KEY` | `backend/.env` | Optional API key gate on `/api/analyze`. |
| `VITE_API_URL` | frontend env | Backend URL for production. Empty = use Vite proxy. |

---

## Key Constraints

- **All agent findings must cite specific numbers** — the `FINDING_RULES` constant in `specialist_agents.py` is injected into every agent system prompt to enforce this. Don't weaken it.
- **Profile values beat extracted values** — `CEOAgent._build_business_model()` explicitly never overwrites non-zero profile fields with Claude's extractions. Maintain this precedent when touching that method.
- **`primary_concern` must flow everywhere** — it's set on `SharedMemory` from the profile form and must appear in the CEO Agent's Phase 1, Phase 3 (synthesis), and Phase 5 (executive summary) prompts.
- **f-string truncation** — see PDF Generation note above. Applies to any large Python file.
