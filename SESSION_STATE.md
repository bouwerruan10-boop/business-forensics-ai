# Imara — Session State / Continue Here
_Saved 2026-06-19. Read this first to resume._

## Where things stand (all GREEN and live)
- **Repo**: `main` @ `9ac1ecc`, GitHub Actions CI **passing** (3 green runs).
- **Backend**: Railway service `web` (project `strong-creativity`) — live on `9ac1ecc`,
  health = `{"service":"Imara v2.0","commit":"9ac1ecc…"}`. **ANTHROPIC_API_KEY + SERPER_API_KEY set & valid.**
- **Frontend**: Vercel `business-forensics-ai.vercel.app` — auto-deploys from `main`, live.
- **A FULL LIVE TEST COMPLETED SUCCESSFULLY** (analysis id `1666b5b3-3fbb-4d57-bc3d-e91ad0e350bb`):
  72 findings, Imara Score **44 / Band D "At Risk"**, all 17+ agents ran (incl. the 4 reconstructed
  agents, SA Tax/Legal, Market Research). Confirms the whole pipeline works in production.

## What was shipped this session (commits on main)
1. `acf49b6` — Imara Score™ composite + **repaired corrupted specialist_agents.py** (4 agents
   reconstructed: Fraud/Credit/Valuation/Forecast) + report integration.
2. `e9c306c` — Hardening: **CI + 11 tests**, Imara confidence indicator, single-source band colour,
   pipeline resilience (per-agent try/except), sub-score cap, CORS lockdown, X-API-Key wiring,
   `/api/health` commit SHA. Fixed `_wrap_flowables` (PDF 500) and `client.js`→`VITE_API_URL`.
3. `7194e16` — fix(ci): committed required `backend/data/benchmarks.json` (was gitignored → missing
   from every Railway build) + made agent tests hermetic.
4. `9ac1ecc` — **Deterministic financial ratios** (`services/financial_ratios.py`): extracts line
   items + computes margins/liquidity/gearing/working-capital days, each traceable to source figures;
   anchors the Imara Profitability component (60/40 blend); "Financial Fundamentals" panel in
   dashboard/PDF/HTML. 6 new tests (17 total pass).

## OPEN ISSUES found by the live test (priority order) — see TaskList #26/#27
1. **#27 Financial extraction empty on summary-statement CSVs** (HIGHEST VALUE).
   Live test: `financial_figures` & `financial_ratios` came back `[]`. `file_parser` is
   transaction-row oriented ("0 rows returned" finding); `extract_financials()` reads
   `memory.uploaded_financial_text`, which lacked clean "Label value" lines for a summary statement.
   → Make extraction read the RAW uploaded cells/text, or have file_parser preserve label,value pairs.
   Repro file: `Sample_Financials_Mzansi_Retail.csv` (in repo root + outputs). Until fixed, the
   Financial Fundamentals panel never renders for statement uploads AND the LLMs drift (finding said
   gross margin 21.3% vs real 33.2%).
2. **PERFORMANCE — ~46 min per analysis** (created 11:48 → completed 12:34). Root cause: ~17 agents
   run SEQUENTIALLY, each makes TWO Claude calls (analyze + `_parse_findings`), large Sonnet prompts.
   → Fix (the staged big win, ~70-85% faster): (a) parallelise Phase-2 agents (independent),
   (b) Anthropic structured outputs to kill the 2nd parse call, (c) prompt caching on the shared
   context prefix. Tests now guard regressions, so it's safe to do agent-by-agent.
3. **#26 AnalysisProgress.jsx UI bugs**: hardcoded "Estimated time: 3-8 minutes" (wrong) and a
   hardcoded 12-agent list/denominator → reconstructed + SA + market agents never get a row and the
   counter reads "18 of 12". Derive list/total/ETA from the real pipeline/status.

## Other known follow-ups (from IMARA_HARDENING_PLAN.md, not yet done)
- Faithfulness verification (reject findings whose numbers aren't traceable to source).
- AHP/back-tested Imara weight calibration. Auth/access-control before real client traffic.
- **Railway is on a LIMITED TRIAL (~$4.97/30 days)** — add a plan before it lapses or backend goes down.

## How to work here (hard rules — see CLAUDE.md / HANDOFF.md)
- **Write large files via bash heredoc**, never the Edit/Write tools (they truncate on this Windows
  mount — corrupted specialist_agents.py, Dashboard.jsx, client.js this project). Prefer Python
  string-replace patching for surgical backend edits. CI now catches truncation.
- **Git from Windows only**: double-click `push_imara.bat` (clears the stale `.git/index.lock` first).
- Recommended next action: start with **#27 (extraction)** — it protects the report's credibility
  and is reproducible with the sample CSV.

## NOTE on git status (not data loss)
On resume, `git status` may show several files as both `D` (deleted) and `??` (untracked) —
Toast.jsx, ValuationPanel.jsx, index.css, main.jsx, tailwind.config.js, vercel.json, vite.config.js,
railway.toml. This is a **sandbox git-index artifact** (stale `.git/index.lock` + line-ending churn),
NOT real deletion. Verified: all files exist on disk with full content AND are committed in HEAD
(`9ac1ecc`), and `origin/main == 9ac1ecc`. Running git from Windows (push_imara.bat clears the lock)
resolves it. `SESSION_STATE.md` itself is uncommitted on disk — add it to a commit if you want it in git.
