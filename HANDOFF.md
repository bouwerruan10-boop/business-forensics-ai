# Imara — Handoff Document
_Last updated: 2026-06-19_

## What Was Just Shipped (this session)

### 1. Imara Score™ — branded composite hero metric
A single 0–100 bankability / investability rating synthesising every specialist
agent output, weighted toward what a lender or investor assesses. Components are
dropped if not produced this run and the remaining weights are re-normalised, so
the score is always 0–100.

| Component | Source | Base weight |
|---|---|---|
| Profitability | `profitability_score` | 25% |
| Credit Readiness | `credit_score` | 20% |
| Risk & Compliance | `risk_score` | 15% |
| Operational Efficiency | `efficiency_score` | 10% |
| Financial Integrity | `100 − fraud_risk_score` | 10% |
| Market Visibility | `market_visibility_score` | 10% |
| Tax Compliance | `100 − sa_tax_risk_score` | 5% |
| Legal Compliance | `100 − sa_legal_risk_score` | 5% |

Bands: A 80–100 *Investment Ready* · B 65–79 *Bankable* · C 50–64 *Developing* ·
D 35–49 *At Risk* · E 0–34 *Distressed*.

- `memory/shared_memory.py` — added `imara_score`, `imara_band`, `imara_label`, `imara_components`.
- `agents/ceo_agent.py` — `_calculate_imara_score()` runs in Phase 4 (after `_score_business`); fields exposed in the report dict.
- `frontend/src/components/ImaraScoreHero.jsx` — NEW gold-accented hero (score ring, band, label, component breakdown). Rendered above the score cards in `Dashboard.jsx` (and therefore in `SharedReport`, which reuses Dashboard).
- `services/report_generator.py` — Imara Score hero block added to the PDF (all 3 audiences), top of the scorecard page.
- `services/html_report.py` — Imara Score hero block added to the top of the HTML report Overview tab.

### 2. CRITICAL REPAIR — `agents/specialist_agents.py` was corrupted
A previous session's Edit-tool truncation had committed a broken file to HEAD
(`81dfa01`): a duplicate `ALL_AGENTS` block spliced into `ForecastAgent`'s prompt
(syntax error), and FOUR agent classes missing entirely — `FraudDetectionAgent`,
`CreditReadinessAgent`, `ValuationAgent`, `ForecastAgent`. The backend could not
import. All four were reconstructed from the surviving `ForecastAgent` fragment,
the SharedMemory field contracts, and house style. `name` strings match exactly
what `ceo_agent._score_business()` expects. Verified: file parses, all 15 agents
resolve, single `ALL_AGENTS`, JSON-extraction + fallback paths tested.

The four reconstructed prompts were then refined with SA-specific grounding
(VAT/EMP201 fraud vectors; prime-rate DSCR + SEFA/IDC/NEF funder fit; SA SME
2.5x–5x EBITDA deal reality; SA macro drivers — energy/load-shedding, prime, CPI,
rand). **JSON output contracts were left unchanged**, so parsing is unaffected.
NOTE: prompts are faithful reconstructions, not byte-identical to the lost originals.

## Current Agent Count (15 in ALL_AGENTS)
Financial → Accounting → Auditor → Operations → Logistics → Sales → Marketing →
HR → Procurement → Strategy → LegalRisk → **Fraud** → **Credit** → **Valuation** →
**Forecast**. (SATaxAgent / SALegalAgent remain excluded — phases 2c/2d.)

## Known Issues / Incomplete Items
- `npm run build` was NOT run in-session: the mounted `node_modules` has Windows
  rollup binaries, not Linux. JSX validated via esbuild instead. Build on Windows.
- `App.jsx` line ~72 still sets `setPhase('upload')` on error (harmless stale ref).
- `BusinessProfile.jsx` and `FileUpload.jsx` are dead code (replaced by SmartIntake).
- A stale `.git/index.lock` may exist from a sandbox session — `push_imara.bat`
  now deletes it before staging.

## Suggested Next Features
1. Email delivery — send the PDF to the client via SendGrid/Resend.
2. Client portal links — generate shareable `SharedReport` links from the dashboard.
3. Report branding / white-labelling — firm logo + name on the PDF.
4. Stripe payment gate (replace the `API_SECRET_KEY` gate).
5. SARS eFiling pre-fill from tax uploads.
6. Afrikaans / Zulu report summaries.

## Critical Rules (Never Break)
1. Write large Python files via bash heredoc — the Edit tool truncates on this Windows mount. (This is what corrupted `specialist_agents.py`. It also truncated `Dashboard.jsx` this session — recovered from git.) Prefer Python string-replace patching for surgical edits.
2. Git writes from the user's Windows terminal via `push_imara.bat` — the sandbox can read git but cannot manage `.git` lock files on this mount.
3. Profile values always win over Claude-extracted values in `_build_business_model()`.
4. SATaxAgent and SALegalAgent stay out of `ALL_AGENTS` — phases 2c/2d.
5. `primary_concern` must appear in CEO Phases 1, 3, and 5 prompts.
6. Imara agent `name` strings must match the sets in `ceo_agent._score_business()`.
