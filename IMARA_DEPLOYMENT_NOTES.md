# Imara — Deployment, Activation & Handoff Notes
*State at handoff, 20 June 2026. Backend on Railway (`web-production-87ff5c.up.railway.app`, health = "Business Forensics AI v2.0"), frontend on Vercel (`business-forensics-ai.vercel.app`). Both auto-deploy from `main`.*

## ⚠️ 1. Make analyses persist (one-time, important)
Railway's container filesystem is **ephemeral**, so the SQLite database is recreated **empty on every redeploy** — which is why stored analyses, share links, and admin history disappear after a deploy. The code now supports a persistent path automatically:
- **Attach a Railway Volume to the backend service** (Railway dashboard → the web service → *Volumes* → add a volume, mount path e.g. `/data`). Railway sets `RAILWAY_VOLUME_MOUNT_PATH`, and the app stores `analyses.db` there — surviving deploys.
- Alternatively, set `BF_DB_PATH` to a persistent path.
Until a volume is attached, every push that redeploys the backend wipes saved reports.

## 2. Security activation (optional but recommended)
- **`ADMIN_API_KEY`** (Railway env) — locks `/api/admin/*` (list/detail/delete of all analyses). Currently **unset → admin is open**. Set it, then enter the key once in the History/admin tab.
- **`API_SECRET_KEY`** (Railway) + **`VITE_API_KEY`** (Vercel) — optional gate on `/api/analyze`.

## 3. Environment variables
| Var | Where | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Railway | **required** — Claude API |
| `SERPER_API_KEY` | Railway | market research (gracefully skipped if absent) |
| `MODEL` / `PARSE_MODEL` | Railway | analysis model / cheap JSON-extraction model (Haiku) |
| `RATE_LIMIT` | Railway | default `3/hour` per IP |
| `CORS_ORIGINS` | Railway | extra allowed origins (Vercel preview already allowed) |
| `ADMIN_API_KEY` | Railway | activate the admin gate |
| `RAILWAY_VOLUME_MOUNT_PATH` / `BF_DB_PATH` | Railway | persistent DB location |
| `VITE_API_URL` | Vercel | backend URL (set to the Railway URL) |

## 4. What's done (this engagement, all CI-green on `main`)
Imara Score + faithfulness + deterministic ratios + eval harness; two rounds of parallelisation (~46 → ~11 min); the full UI overhaul (accessibility, section nav, charts, stepped intake, methodology + data-coverage panels); monotonic/honest progress ETA; restart-resilience; admin gate; expiring/revocable share links; AI structured-extraction fallback for messy statements; and the **Action Simulator** (prescriptive outcome simulation) with **v2** (Monte Carlo likelihood + sensitivity "biggest levers" + tax/plausibility guards). 40 backend tests.

## 5. Open items that need YOUR input or real data (not done autonomously)
- **Per-user accounts / auth model** — needs a product call: client logins vs operator-only vs magic-link share. (Share links + admin gate are shipped; full multi-tenant auth is the larger next step.)
- **Imara Score weight calibration + GTM wedge** (B2C vs B2B-to-lenders) — need real outcome data to back-test.
- **Simulator next rungs** — optimiser ("best bundle under a budget"), time-phased monthly trajectory, calibration of the haircuts/elasticity against actuals.

## 6. Verification state at handoff
40 backend tests pass; `main` deploys green on both Railway and Vercel. The **Action Simulator v2** is unit-tested and deployed, but a live click-through was still pending at handoff (the browser tool was unavailable, and the live DB was empty pending the volume in §1). Quickest live check once a volume is attached: run one analysis, open the report, scroll to **Action Simulator**, tick an action — confirm the projected score, the "biggest levers" strip, and the "≈X% chance of reaching Band Y" likelihood all render.
