# Claude Code Prompt — Business Forensics AI

Use this prompt when starting a Claude Code session on this project.

---

## Paste this into Claude Code:

```
You are working on Business Forensics AI — a solo consulting platform where clients upload Excel/CSV/PDF business data and 11 specialist Claude agents produce a McKinsey-quality PDF report.

Read CLAUDE.md first before touching any file. It contains the architecture, pipeline flow, critical constraints, and known bugs you must follow.

Key rules before you write a single line:

1. READ CLAUDE.md — it explains the full agent pipeline, SharedMemory contract, benchmark system, file parser quirks, and frontend state machine.

2. F-STRING TRUNCATION BUG — any Python file you rewrite that contains f-strings with complex expressions (dict keys, method calls, HTML) WILL be silently truncated by file-editing tools. Always rewrite large Python files using bash heredoc:
   cat > backend/services/example.py << 'PYEOF'
   ...file contents using .format() instead of f-strings...
   PYEOF
   Then verify: python3 -c "import ast; ast.parse(open('backend/services/example.py').read())"

3. NEVER overwrite profile-provided values — in CEOAgent._build_business_model(), annual_revenue, headcount, and currency from the user's profile form always win over Claude's extractions from the uploaded files. Do not change this logic.

4. primary_concern must flow — it lives on SharedMemory and must appear in CEO Agent Phase 1, Phase 3 (synthesis), and Phase 5 (executive summary) prompts. If you add new prompts, check whether primary_concern is relevant.

5. All findings must cite numbers — the FINDING_RULES constant in agents/specialist_agents.py is injected into every agent. Do not weaken or remove it.

6. Chart calls are always wrapped in try/except — services/charts.py failures must never crash PDF generation.

7. SQLite writes always use the module-level _lock in services/database.py — do not add any direct sqlite3 calls outside that module.

Project structure at a glance:
  backend/main.py                    — FastAPI endpoints, background task runner
  backend/agents/ceo_agent.py        — 5-phase orchestration pipeline
  backend/agents/specialist_agents.py — 11 domain agents + ALL_AGENTS list
  backend/agents/base_agent.py       — BaseAgent with _call_claude, _parse_findings
  backend/memory/shared_memory.py    — SharedMemory dataclass, AgentFinding dataclass
  backend/services/benchmark_service.py — industry detection + benchmark prompt builder
  backend/services/file_parser.py    — Excel/CSV/PDF parsing with messy-data handling
  backend/services/report_generator.py  — ReportLab PDF generation
  backend/services/charts.py         — matplotlib chart PNG generation
  backend/services/database.py       — SQLite persistence (thread-safe)
  backend/data/benchmarks.json       — 20 industry profiles incl. African market data
  frontend/src/App.jsx               — phase state machine (profile→upload→analyzing→done|admin)
  frontend/src/components/           — Dashboard, AdminDashboard, ScoreCards, AgentActivity

Now tell me what you want to build or fix.
```
