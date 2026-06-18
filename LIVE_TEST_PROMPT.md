# Claude Code — Live End-to-End Test Prompt

Use this prompt AFTER you have added your ANTHROPIC_API_KEY to backend/.env

---

## Paste this into Claude Code:

```
Run a live end-to-end test of the full pipeline. The API key is now in backend/.env

STEP 1 — Confirm the key is present (never print it):
  grep -c "ANTHROPIC_API_KEY=sk-" backend/.env && echo "Key present" || echo "Key missing"

STEP 2 — Start the backend:
  cd backend
  uvicorn main:app --port 8000 &
  sleep 3
  curl -s http://localhost:8000/api/health | python3 -m json.tool

STEP 3 — Run the end-to-end test with the correct API field names:
  python3 << 'PYEOF'
import requests, time, json

# Minimal 3-month P&L test file
with open("/tmp/test_data.csv", "w") as f:
    f.write("Month,Revenue,Cost_of_Sales,Gross_Profit,Labour,Rent,Other_Expenses,Net_Profit\n")
    f.write("Jan,500000,310000,190000,95000,18000,22000,55000\n")
    f.write("Feb,520000,325000,195000,97000,18000,23000,57000\n")
    f.write("Mar,480000,300000,180000,93000,18000,21000,48000\n")

profile = {
    "company_name":   "Mzansi Trading Co",
    "industry_key":   "retail",
    "annual_revenue": "6000000",
    "headcount":      "25",
    "currency":       "ZAR",
    "country":        "South Africa",
    "primary_concern": "Our margins are shrinking every month",
}

print("Uploading test data...")
with open("/tmp/test_data.csv", "rb") as f:
    r = requests.post(
        "http://localhost:8000/api/analyze",
        data=profile,
        files=[("files", ("test_data.csv", f, "text/csv"))],
    )

if r.status_code != 200:
    print("FAIL — analyze endpoint returned", r.status_code)
    print(r.text[:500])
    exit(1)

analysis_id = r.json()["analysis_id"]
print("Analysis started:", analysis_id)

# Poll until done or error (max 12 minutes)
for i in range(144):
    s = requests.get(f"http://localhost:8000/api/status/{analysis_id}").json()
    agent = s.get("current_agent", "—")
    print(f"  [{i*5:>3}s] {s['status']:<12} {agent}")
    if s["status"] in ("complete", "error"):
        break
    time.sleep(5)

print("\nFinal status:", s["status"])

if s["status"] == "complete":
    report = requests.get(f"http://localhost:8000/api/report/{analysis_id}").json()
    findings = report.get("all_findings_ranked", [])
    scores = report.get("scores", {})

    print("\n── REPORT SUMMARY ──────────────────────────────────")
    print("Business name:  ", report.get("business_name"))
    print("Industry:       ", report.get("industry"))
    print("Scores:          health={} profitability={} efficiency={} risk={}".format(
        scores.get("business_health"), scores.get("profitability"),
        scores.get("efficiency"), scores.get("risk"),
    ))
    print("Total findings: ", report.get("total_findings"))
    print("Critical:       ", report.get("critical_findings"))
    print("High:           ", report.get("high_findings"))

    print("\n── TOP 3 FINDINGS ──────────────────────────────────")
    for f in findings[:3]:
        print(f"  [{f.get('severity','?').upper()}] {f.get('title','')}")
        print(f"    Impact: {f.get('financial_impact','')}")

    print("\n── QUICK WINS ──────────────────────────────────────")
    qw = [f for f in findings if f.get("quick_win")]
    print(f"  {len(qw)} quick wins identified (of top 20 ranked)")

    pdf = requests.get(f"http://localhost:8000/api/report/{analysis_id}/pdf")
    print("\n── PDF ─────────────────────────────────────────────")
    print(f"  Size: {len(pdf.content):,} bytes")
    print(f"  Valid PDF: {pdf.content[:4] == b'%PDF'}")

    print("\n✅ END-TO-END TEST PASSED")

else:
    print("Pipeline error:", s.get("error", "")[:400])
    print("\n❌ END-TO-END TEST FAILED")
PYEOF

STEP 4 — Kill the dev server:
  pkill -f "uvicorn main:app" 2>/dev/null || true

STEP 5 — If the test passed, print a final project summary for the user:
  git log --oneline
  echo ""
  echo "Project is complete and ready to deploy."
  echo "See DEPLOY_PROMPT.md for Railway + Vercel deployment instructions."

If the test failed, debug the error before finishing — check:
  1. Is the error from the Claude API itself (rate limit, invalid key)?
  2. Is it a Python exception in the agent pipeline?
  3. Is the report shape different from expected?
Fix the bug, commit the fix, then re-run from STEP 2.
```
