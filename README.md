# Business Forensics AI — Virtual Consulting Firm

> **⚠️ CONFIDENTIAL & PROPRIETARY — NOT OPEN SOURCE.** Copyright © 2026 Ruan Bouwer. All rights reserved.
> This repository contains trade-secret material. No right is granted to use, copy, modify, distribute, or
> reverse-engineer it. See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), and
> [`IMARA_CODE_CONFIDENTIALITY.md`](IMARA_CODE_CONFIDENTIALITY.md).

An AI-powered business analysis platform. Upload your Excel, CSV, or PDF files and 11 specialist Claude agents analyse every department, identify profit leaks, and generate a full consulting report with PDF download.

---

## Quick Start

### 1. Clone / open the project folder

The project lives at:
```
business-forensics-ai/
├── backend/
└── frontend/
```

### 2. Set up your API key (IMPORTANT — read carefully)

```bash
cd backend
cp .env.example .env
```

Open `.env` in any text editor (Notepad, VS Code, etc.) and replace `your_claude_api_key_here` with your Anthropic API key.

**Never paste your API key in chat or share it anywhere.** It goes only in this `.env` file.

Get your key at: https://console.anthropic.com/settings/keys

### 3. Install Python backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

> On some systems use `pip3` instead of `pip`.

### 4. Install frontend dependencies

```bash
cd frontend
npm install
```

### 5. Run the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### 6. Run the frontend (new terminal window)

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Usage

1. **Upload files** — drag and drop your business data (Excel, CSV, or PDF). Accepted file types: `.xlsx`, `.xls`, `.csv`, `.pdf`
2. **Run analysis** — click "Run Full Forensic Analysis"
3. **Watch agents work** — 11 specialist agents run sequentially (3–6 minutes)
4. **Review results** — Executive Summary, All Findings, 90-Day Roadmap tabs
5. **Download PDF** — click "Download Report" for the full consulting report
6. **Simulate** — use the Digital Twin tab to model revenue/cost changes

### What to upload

The more data you provide, the better the analysis:

| File type | What to include |
|-----------|----------------|
| Excel | P&L statements, balance sheets, payroll exports, sales reports, inventory data |
| CSV | Bank statements, transaction logs, CRM exports, operational metrics |
| PDF | Financial reports, contracts, audit reports, management accounts |

---

## Architecture

```
frontend (React + Vite)  →  backend (FastAPI)  →  Claude API
     localhost:5173              localhost:8000

Agents:
  CEO Agent (orchestrator)
  ├── Financial Forensics
  ├── Accounting
  ├── Auditor
  ├── Operations
  ├── Logistics
  ├── Sales
  ├── Marketing
  ├── Human Resources
  ├── Procurement
  ├── Strategy
  └── Legal Risk
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Claude API key | **required** |
| `MODEL` | Claude model to use | `claude-sonnet-4-6` |
| `MAX_TOKENS` | Max tokens per agent call | `4096` |

---

## Cloud Deployment

### Deploy backend (e.g. Railway, Render, Fly.io)

1. Push `backend/` to a repo
2. Set `ANTHROPIC_API_KEY` as an environment variable in your hosting provider's dashboard
3. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Deploy frontend (e.g. Vercel, Netlify)

1. Update `vite.config.js` proxy target to point at your deployed backend URL
2. Or set `VITE_API_URL` environment variable and update `frontend/src/api/client.js` to use it
3. Build command: `npm run build` — deploy the `dist/` folder

### Docker (optional)

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Project Structure

```
business-forensics-ai/
├── backend/
│   ├── .env.example          # Copy to .env and add your API key
│   ├── .env                  # Your actual keys — never commit this
│   ├── requirements.txt
│   ├── config.py             # Loads environment variables
│   ├── main.py               # FastAPI app + endpoints
│   ├── memory/
│   │   └── shared_memory.py  # Shared context across all agents
│   ├── agents/
│   │   ├── base_agent.py     # Base class with Claude calling logic
│   │   ├── specialist_agents.py  # All 11 specialist agents
│   │   └── ceo_agent.py      # Orchestrator — runs the full pipeline
│   └── services/
│       ├── file_parser.py    # Excel / CSV / PDF parsing
│       └── report_generator.py  # PDF report generation (ReportLab)
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx            # Root component — phase state machine
        ├── main.jsx
        ├── api/
        │   └── client.js      # API calls to backend
        └── components/
            ├── FileUpload.jsx  # Drag-and-drop file input
            ├── AgentActivity.jsx  # Live agent progress panel
            ├── ScoreCards.jsx  # Radial score rings
            └── Dashboard.jsx   # Full report with tabs + simulator
```

---

## Troubleshooting

**`ANTHROPIC_API_KEY not found` error**
→ Make sure `.env` exists in the `backend/` folder (not `.env.example`), and your key is on the `ANTHROPIC_API_KEY=` line with no spaces.

**`ModuleNotFoundError` on startup**
→ Run `pip install -r requirements.txt` again from inside the `backend/` folder.

**Frontend shows blank page**
→ Check that the backend is running on port 8000. Check browser console for errors.

**Analysis takes a long time**
→ Normal — 11 agents each make multiple Claude API calls. Expect 3–8 minutes for large files.

**PDF is empty or missing sections**
→ The PDF is generated from the JSON report. If the analysis timed out or errored, retry with smaller files.
