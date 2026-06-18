# Claude Code — Deployment & Polish Prompt

---

## Paste this into Claude Code:

```
The full stack is built and pushed. The next session has two goals:
1. Verify the complete end-to-end pipeline works with a real API key
2. Prepare the project for cloud deployment (backend on Railway/Render, frontend on Vercel)

Read CLAUDE.md before touching any file.

STEP 1 — Audit current state:
  git log --oneline
  find backend -name "*.py" | sort
  find frontend/src -type f | sort
  cd backend && python3 -c "from agents.ceo_agent import CEOAgent; print('imports OK')"
  cd frontend && npm run build 2>&1 | tail -5

──────────────────────────────────────────────────────────────
PHASE 10 — End-to-end smoke test (no commit needed)
──────────────────────────────────────────────────────────────
Check backend/.env exists and has ANTHROPIC_API_KEY set:
  cat backend/.env | grep -v KEY  # print non-key lines only (never print the key)

If .env is missing or the key is placeholder:
  echo "ANTHROPIC_API_KEY is not set — skipping live test, continuing to deployment prep"
  (Do not stop — proceed to Phase 11)

If the key IS set, run a live smoke test:
  cd backend
  uvicorn main:app --port 8000 &
  sleep 2

  # Upload a minimal test CSV and confirm the full pipeline runs
  python3 << 'PYEOF'
  import requests, time, json

  # Create minimal test CSV
  with open("/tmp/test_data.csv", "w") as f:
      f.write("Month,Revenue,Expenses,Profit\n")
      f.write("Jan,500000,380000,120000\n")
      f.write("Feb,520000,395000,125000\n")
      f.write("Mar,480000,370000,110000\n")

  profile = {
      "company_name": "Test Trading Co",
      "industry": "retail",
      "annual_revenue": "6000000",
      "headcount": "25",
      "currency": "ZAR",
      "country": "South Africa",
      "primary_concern": "Margins are shrinking",
  }

  with open("/tmp/test_data.csv", "rb") as f:
      r = requests.post(
          "http://localhost:8000/api/analyze",
          data=profile,
          files=[("files", ("test_data.csv", f, "text/csv"))],
      )

  print("Analyze status:", r.status_code)
  if r.status_code != 200:
      print(r.text[:500])
      exit(1)

  analysis_id = r.json()["analysis_id"]
  print("Analysis ID:", analysis_id)

  # Poll until done or error (max 10 minutes)
  for i in range(120):
      s = requests.get(f"http://localhost:8000/api/status/{analysis_id}").json()
      print(f"  [{i*5}s] status={s['status']} agent={s.get('current_agent','')}")
      if s["status"] in ("complete", "error"):
          break
      time.sleep(5)

  print("Final status:", s["status"])
  if s["status"] == "complete":
      r2 = requests.get(f"http://localhost:8000/api/report/{analysis_id}")
      report = r2.json()
      print("Report keys:", list(report.keys()))
      print("Findings:", report.get("total_findings"), "total")
      print("Health score:", report.get("scores", {}).get("business_health"))
      pdf = requests.get(f"http://localhost:8000/api/report/{analysis_id}/pdf")
      print("PDF size:", len(pdf.content), "bytes, starts with:", pdf.content[:4])
  else:
      print("Error:", s.get("error", "")[:300])
  PYEOF

  # Kill dev server
  pkill -f "uvicorn main:app" 2>/dev/null || true

If any step fails, fix the bug before continuing to Phase 11.

──────────────────────────────────────────────────────────────
PHASE 11 — Deployment files (commit: "feat: deployment config")
──────────────────────────────────────────────────────────────

backend/Dockerfile:
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  RUN mkdir -p data
  CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

backend/.dockerignore:
  .env
  __pycache__
  *.pyc
  data/*.db

backend/railway.toml:
  [build]
  builder = "dockerfile"

  [deploy]
  startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
  healthcheckPath = "/api/health"
  healthcheckTimeout = 30
  restartPolicyType = "on_failure"

  [environments.production.variables]
  MODEL = "claude-sonnet-4-6"
  MAX_TOKENS = "4096"
  RATE_LIMIT = "10/hour"

frontend/vercel.json:
  {
    "rewrites": [{ "source": "/api/(.*)", "destination": "/__proxy__/api/$1" }],
    "env": {
      "VITE_API_URL": ""
    },
    "buildCommand": "npm run build",
    "outputDirectory": "dist",
    "framework": "vite"
  }

  NOTE: In the actual Vercel dashboard, set VITE_API_URL to the Railway backend URL,
  e.g. https://your-app.railway.app — the frontend reads this at build time.

.gitignore at repo root:
  backend/.env
  backend/data/*.db
  backend/data/uploads/
  frontend/node_modules/
  frontend/dist/
  __pycache__/
  *.pyc
  .DS_Store

──────────────────────────────────────────────────────────────
PHASE 12 — Final polish (commit: "feat: UX polish + error handling")
──────────────────────────────────────────────────────────────

Fix these items in order:

1. backend/main.py — add upload size guard:
   If total uploaded file size > 50MB, return HTTP 413 with message
   "Files too large. Maximum total upload size is 50MB."

2. backend/main.py — ensure /api/health returns backend version and model:
   { "status": "ok", "model": MODEL, "rate_limit": RATE_LIMIT, "version": "2.0.0" }

3. frontend/src/components/FileUpload.jsx — add file size display:
   Show each file's size next to its name (e.g. "financials.xlsx  •  2.4 MB")

4. frontend/src/App.jsx — improve error display during analyzing phase:
   If status.status === 'error', show the error message in a red card
   with a "Try Again" button that resets phase to 'upload'

5. frontend/src/components/Dashboard.jsx — make PDF button show loading state:
   When clicked, show "Generating PDF…" and disable the button for 3 seconds
   (PDF generation takes a moment; prevents double-clicks)

6. README.md — update the Project Structure section to reflect what was actually built:
   Add: AdminDashboard.jsx, ScoreCards.jsx, AgentActivity.jsx, theme.js
   Add the new backend files: services/charts.py, services/database.py,
   memory/shared_memory.py, agents/specialist_agents.py

After all edits, run:
  cd backend && python3 -c "import ast; [ast.parse(open(f).read()) for f in __import__('glob').glob('**/*.py', recursive=True)]" && echo "All Python OK"
  cd frontend && npm run build && echo "Frontend build OK"

Commit all Phase 12 changes together.

──────────────────────────────────────────────────────────────
STEP 3 — Final push and deployment instructions
──────────────────────────────────────────────────────────────
  git push

Then print clear deployment instructions for the user:

BACKEND (Railway):
  1. Go to railway.app → New Project → Deploy from GitHub repo
  2. Select the repo, set root directory to: backend/
  3. Add environment variable: ANTHROPIC_API_KEY = <your key>
  4. Railway auto-detects the Dockerfile and deploys
  5. Copy the generated URL (e.g. https://your-app.railway.app)

FRONTEND (Vercel):
  1. Go to vercel.com → New Project → Import GitHub repo
  2. Set root directory to: frontend/
  3. Add environment variable: VITE_API_URL = https://your-app.railway.app
  4. Deploy — Vercel auto-detects Vite
  5. Your app is live at the Vercel URL

LOCAL (for testing with a real key):
  cd backend && ANTHROPIC_API_KEY=your_key uvicorn main:app --port 8000
  cd frontend && npm run dev
  Open http://localhost:3000
```
