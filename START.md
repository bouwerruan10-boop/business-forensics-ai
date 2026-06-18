# Business Forensics AI — Quick Start

## Prerequisites
- Python 3.10+
- Node.js 18+
- ANTHROPIC_API_KEY set as an environment variable

## 1. Backend

```powershell
cd business-forensics-ai\backend
pip install -r requirements.txt
uvicorn main:app --port 8000
```

Health check: http://localhost:8000/api/health

## 2. Frontend

```powershell
cd business-forensics-ai\frontend
npm install
npm run dev
```

Open: http://localhost:3000

## Environment

The backend reads `ANTHROPIC_API_KEY` from your process environment.
Do NOT put the real key in the `.env` file — it's already configured to use
the process env variable.

To set it in PowerShell for the current session:
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

## Share URLs

After an analysis completes, click "Copy Share Link" to copy a URL like:
`http://localhost:3000/#/report/<id>`

Anyone with the link can view the full report (read-only, no auth required).

## Notes

- Analysis takes 3–8 minutes depending on file size
- SQLite database is stored in `backend/data/analyses.db`
- PDF reports are generated on demand — no storage required
