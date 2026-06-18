# Claude Code — Frontend Build Prompt

---

## Paste this into Claude Code:

```
The backend is complete and pushed. Now build the entire React/Vite frontend.
Read CLAUDE.md first — it documents the phase state machine and every component.

STEP 1 — Audit what exists before writing anything:
  find frontend -type f | sort
  git log --oneline

STEP 2 — Build the frontend in this order. Commit each phase separately.

──────────────────────────────────────────────────────────────
PHASE 5 — Project scaffold (commit: "feat: frontend scaffold")
──────────────────────────────────────────────────────────────
  frontend/package.json
    dependencies: react, react-dom, recharts, lucide-react
    devDependencies: @vitejs/plugin-react, vite
    scripts: dev, build, preview

  frontend/vite.config.js
    - dev server on port 3000
    - proxy /api/* to http://localhost:8000

  frontend/index.html
    - dark background #0D1B2A, mounts <div id="root">

  frontend/.gitignore
    node_modules/, dist/

After writing these, run: cd frontend && npm install
Confirm no errors before continuing.

──────────────────────────────────────────────────────────────
PHASE 6 — API client + App shell (commit: "feat: App state machine + API client")
──────────────────────────────────────────────────────────────
  frontend/src/main.jsx
    - ReactDOM.createRoot, renders <App />
    - global CSS: body background #0D1B2A, color #f0f0f0, font-family sans-serif, margin 0

  frontend/src/api/client.js
    - API_BASE = import.meta.env.VITE_API_URL || ''
    - uploadFiles(files, profile) → POST /api/analyze multipart
    - pollStatus(id) → GET /api/status/{id}
    - getReport(id) → GET /api/report/{id}

  frontend/src/App.jsx
    Phase state machine — phase: profile | upload | analyzing | done | admin
    - profile  → renders <BusinessProfile onComplete={fn} />
    - upload   → renders <FileUpload onAnalyze={fn} /> + agent chip list
    - analyzing → polls /api/status every 2s, renders progress bar + <AgentActivity />
    - done     → renders <Dashboard report={report} analysisId={id} />
    - admin    → renders <AdminDashboard onViewReport={fn} />

    Nav bar:
    - Gold dot + "BUSINESS FORENSICS AI" + "Virtual Consulting Firm"
    - "Admin" toggle button (gold when active)
    - "New Analysis" button (only when phase === 'done')

    Step indicator (only during profile/upload phases):
    - 2 numbered circles: "Business Profile" and "Upload Files"
    - Gold fill for completed/current step, connected by a line

──────────────────────────────────────────────────────────────
PHASE 7 — Input components (commit: "feat: BusinessProfile + FileUpload")
──────────────────────────────────────────────────────────────
  frontend/src/components/BusinessProfile.jsx
    Fields (all in one dark card form):
    - Company Name (text, required)
    - Industry (text, e.g. "Retail grocery, logistics, hospitality")
    - Annual Revenue (number)
    - Headcount (number)
    - Currency (select: ZAR, USD, EUR, GBP, KES, NGN)
    - Country (text)
    - Primary Concern (textarea — "What keeps you up at night?")

    Style: dark navy #0D1B2A background, gold #C9A84C accents,
    input fields with rgba(255,255,255,0.05) background,
    gold "Continue →" submit button

  frontend/src/components/FileUpload.jsx
    - Drag-and-drop zone accepting .xlsx .xls .csv .pdf
    - File list with remove buttons
    - Gold "Run Full Forensic Analysis" submit button
    - Accepted file type chips shown below the zone

──────────────────────────────────────────────────────────────
PHASE 8 — Analysis + results components (commit: "feat: Dashboard + AgentActivity + ScoreCards")
──────────────────────────────────────────────────────────────
  frontend/src/components/AgentActivity.jsx
    Live agent progress panel (shown during analyzing phase):
    - List of all 11 agents + CEO Agent
    - Current agent highlighted gold with a spinner
    - Completed agents shown with a green checkmark
    - Receives status prop from App.jsx

  frontend/src/components/ScoreCards.jsx
    Four score rings using recharts RadialBarChart:
    - Business Health, Profitability, Efficiency, Risk Management
    - Color coded: green ≥70, orange ≥45, red <45
    - Score value centred inside each ring
    - Receives report.scores prop

  frontend/src/components/Dashboard.jsx
    Tabbed report view with 4 tabs:

    Tab 1 — Executive Summary:
    - ScoreCards row at top
    - Situation / Complication / Resolution paragraphs (McKinsey SCR)
    - Executive summary text block
    - Top priority issues list (ranked, with severity badge + financial impact)
    - Quick wins section

    Tab 2 — All Findings:
    - Filterable by severity (critical / high / medium / low)
    - Each finding card: title, detail, financial_impact, recommendation,
      roi_estimate, cost_of_inaction, benchmark_reference, quick_win badge
    - Grouped by department (agent name)

    Tab 3 — 90-Day Roadmap:
    - Three phase cards (Phase 1: Days 1-30, Phase 2: Days 31-60, Phase 3: Days 61-90)
    - Each card: focus headline, action list with owner + impact, expected_impact total

    Tab 4 — Digital Twin:
    - Sliders for revenue change %, cost change %, headcount change %
    - Live calculated output: projected revenue, projected profit, headcount impact
    - Uses report.digital_twin_parameters as base values

    Header bar:
    - Company name, industry, health score badge
    - "Download PDF" button → GET /api/report/{id}/pdf (opens in new tab)

──────────────────────────────────────────────────────────────
PHASE 9 — Admin dashboard (commit: "feat: AdminDashboard")
──────────────────────────────────────────────────────────────
  frontend/src/components/AdminDashboard.jsx
    - Fetches GET /api/admin/analyses?limit=200
    - 4 stat cards: Total / Completed / Processing / Errors
    - Search bar (company, industry, country)
    - Status filter tabs: All / Complete / Processing / Error
    - Table rows: Company+industry, Revenue, Headcount, StatusBadge,
      created_at/completed_at, Actions (View + PDF link + Delete)
    - Delete calls DELETE /api/admin/analyses/{id}
    - View calls onViewReport(id) which fetches /api/report/{id} and switches to done phase
    - Auto-refresh every 15s when any row is processing

Style rules (apply to ALL components):
  - Background: #0D1B2A (dark navy)
  - Card/surface: rgba(255,255,255,0.03) with 1px rgba(255,255,255,0.08) border
  - Gold accent: #C9A84C
  - Text: #f0f0f0 primary, #94a3b8 secondary, #64748b muted
  - Danger/error: #C0392B
  - Success/complete: #27AE60
  - Border radius: 8–12px on cards
  - No external CSS files — all styles inline or in <style> tags within components
  - No Tailwind, no CSS modules — inline style objects only

STEP 3 — After all phases are committed, run the full verification:
  cd frontend && npm run build
  # Must complete with no errors and produce dist/

Then start both servers and confirm the UI loads:
  cd backend && uvicorn main:app --port 8000 &
  cd frontend && npm run dev

CRITICAL: Do not install any npm packages beyond what is in package.json.
The stack is: react, react-dom, recharts, lucide-react, vite, @vitejs/plugin-react.
No router library — App.jsx phase state is the only navigation.
No Tailwind — inline styles only.
```
