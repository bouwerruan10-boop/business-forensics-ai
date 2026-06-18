# Claude Code — Continuation Prompt

Paste this at the start of a new Claude Code session to resume without repeating or breaking work.

---

## Paste this into Claude Code:

```
A previous Claude Code session ran out of context mid-way through building this project.
Your job is to resume cleanly — no rework, no overwriting files that already exist.

STEP 1 — Orient yourself before touching anything:

1. Read CLAUDE.md in the repo root. This is the authoritative architecture reference.

2. Run this audit to see what already exists:
   find backend -type f | sort
   find frontend -type f | sort

3. For every Python file that exists, verify it is not truncated:
   for f in $(find backend -name "*.py"); do
     python3 -c "import ast; ast.parse(open('$f').read())" && echo "OK: $f" || echo "BROKEN: $f"
   done

4. Check git log to see what was already committed:
   git log --oneline

5. Test imports on what exists:
   cd backend && python3 -c "
   try:
     from memory.shared_memory import SharedMemory, AgentFinding; print('SharedMemory OK')
   except Exception as e: print('SharedMemory FAIL:', e)
   try:
     from agents.base_agent import BaseAgent; print('BaseAgent OK')
   except Exception as e: print('BaseAgent FAIL:', e)
   try:
     from agents.specialist_agents import ALL_AGENTS; print('ALL_AGENTS OK:', len(ALL_AGENTS), 'agents')
   except Exception as e: print('specialist_agents FAIL:', e)
   try:
     from agents.ceo_agent import CEOAgent; print('CEOAgent OK')
   except Exception as e: print('CEOAgent FAIL:', e)
   try:
     from services.database import init_db; print('database OK')
   except Exception as e: print('database FAIL:', e)
   try:
     from services.benchmark_service import detect_industry; print('benchmark_service OK')
   except Exception as e: print('benchmark_service FAIL:', e)
   try:
     from services.file_parser import parse_file; print('file_parser OK')
   except Exception as e: print('file_parser FAIL:', e)
   try:
     from services.charts import generate_report_charts; print('charts OK')
   except Exception as e: print('charts FAIL:', e)
   try:
     from services.report_generator import generate_pdf_report; print('report_generator OK')
   except Exception as e: print('report_generator FAIL:', e)
   try:
     import main; print('main.py OK')
   except Exception as e: print('main.py FAIL:', e)
   "

STEP 2 — Based on what is missing or broken, continue building:

The full build plan has 4 phases (details in CLAUDE.md):
  Phase 1: backend core contracts (config, SharedMemory, AgentFinding, requirements.txt, .env.example)
  Phase 2: base agent + 11 specialist agents + CEO agent
  Phase 3: services (file_parser, benchmark_service, benchmarks.json, database, charts, report_generator)
  Phase 4: FastAPI main.py with all endpoints + frontend React app

Start from the first phase that has missing or broken files. Skip anything that passes the import check above.

If a file exists but is BROKEN (ast.parse fails), rewrite it from scratch using bash heredoc:
  cat > backend/path/to/file.py << 'PYEOF'
  ...full file contents...
  PYEOF

STEP 3 — After completing any phase, commit it:
  git add -A && git commit -m "feat: <phase description>"

CRITICAL RULES — never violate these (they are documented in CLAUDE.md):

1. F-STRING TRUNCATION: Any large Python file written by file-editing tools that contains
   f-strings with complex expressions will be silently truncated. Always use bash heredoc
   for files longer than ~50 lines. Use .format() instead of f-strings.
   Verify every file after writing:
   python3 -c "import ast; ast.parse(open('filename.py').read())"

2. PROFILE VALUES WIN: In CEOAgent._build_business_model(), annual_revenue, headcount,
   and currency from the user's profile form must NEVER be overwritten if already non-zero.

3. PRIMARY CONCERN: SharedMemory.primary_concern must appear in CEO Agent Phase 1,
   Phase 3 (synthesis), and Phase 5 (executive summary) prompts.

4. FINDING_RULES: The FINDING_RULES constant must be appended to every specialist
   agent's system_prompt. Do not weaken or remove it.

5. THREAD SAFETY: Every SQLite operation in services/database.py must use the
   module-level threading.Lock(). No direct sqlite3 calls outside that module.

6. CHART SAFETY: Every chart call in services/report_generator.py must be
   wrapped in try/except — chart failures must never crash PDF generation.

7. ALL_AGENTS: The 11 specialist agents are:
   FinancialAgent, AccountingAgent, AuditorAgent, OperationsAgent, LogisticsAgent,
   SalesAgent, MarketingAgent, HRAgent, ProcurementAgent, StrategyAgent, LegalRiskAgent
   All must be in ALL_AGENTS list in agents/specialist_agents.py.

8. AFRICAN BENCHMARKS: benchmarks.json must include south_africa_sme, nigeria_general,
   kenya_general, zimbabwe_general profiles. These are excluded from keyword scan in
   detect_industry() and activate only as country fallback.

Run STEP 1 first. Report back what is present, broken, or missing — then continue.
```
