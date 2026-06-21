# Imara — "Lender's-Eye View" build (research-driven)
*From the Reddit research cycle (IMARA_AGENTS_AND_REDDIT_RESEARCH.md). Goal: make Imara answer the rejection-moment question that owners, accountants, and lenders all circle around — "why would a lender decline me, and what's my true earning power?" — deterministically.*

## Why (evidence)
- Owners can't self-assess and get declined opaquely; lenders said the deciding signals are cash-flow, not credit: inconsistent deposits, low average balance, overdrafts, negative-cash-flow months, and **bank statements telling a different story than the financials**.
- Accountants + SA banks both want the **tax-books → deal/loan-books** translation: owner add-backs, normalized/adjusted EBITDA, EBITDA trend, and (SA) salary-not-loan-account structure.

## Builds (all deterministic; agents only narrate)
1. **normalization.py** — owner/personal/one-off add-back detection → indicative Adjusted EBITDA / SDE range (conservative↔optimistic), labelled "confirm with owner". + SA director's-loan-vs-salary flag (SARS deemed-dividend/interest risk AND the bankability cost of no payslips).
2. **lender_view.py** — (a) reconcile declared revenue vs annualized bank deposits → gap flag; (b) average daily balance + deposit consistency + NSF/negative-month counts (built on bank_signals, minimally extended); (c) indicative borrowing-capacity range (deposit-based working-capital + EBITDA/DSCR term view); (d) decline-risk level + ranked reasons mirroring the exact lender criteria + concrete fix actions.
3. **Wiring** — attach report["normalization"] + report["lender_view"] in the analysis tail; GET /api/report/{id}/lender-view and /normalization; enrich demo-001.
4. **Tests** — unit (edge cases: no bank text, no figures, string figures, clean vs distressed) + integration endpoints; full suite green.
5. **Frontend** — LenderView.jsx panel (decline-risk verdict + reconciliation + ADB/deposits + borrowing range + adjusted-EBITDA range), nav/section 'lender-view'.
6. **Ship** — push_imara.bat; live-verify endpoints on demo-001.

## Guardrails
Indicative, decision-support only (NOT new Imara Score components; NOT a credit decision — consistent with the FAIS/NCA governance framing). Every rand figure traces to uploaded text or computed arithmetic; nothing invented.
