# Dossier Build Plan — the buildable backlog (2026-06-29)

Derived from `docs/research/IMARA_DOSSIER_RECONCILIATION_2026-06.md`. Every item below needs **no
design partner** — they close the dossier's remaining real gaps from inside the product. All obey
the engine DNA: deterministic numbers in `services/`, LLM never invents a figure, pressure-test +
regression test each, surface through all layers, decision-support framing (not a credit decision).
Ordered by leverage. Tier-0 (a design partner feeding labelled outcomes) stays the real unlock and
is Ruan-led — none of the below substitutes for it.

## 1. Reg 23A affordability record (D1) — `services/affordability.py`
- **Why:** the one "CRITICAL" that's an actual build gap. NCA/Reg 23A expects a *documented*
  affordability assessment (income → existing obligations → discretionary income → debt-service vs
  proposed instalment). Today only an *indicative* debt-service view exists (`lender_view.borrowing_capacity`).
- **Build:** `assess_affordability(figures, normalization, bank, proposed_annual_instalment=None)` →
  income-available-for-debt-service (adjusted EBITDA, reuse `normalization.adjusted_ebitda_low`),
  existing annual debt service (`interest` + indicative principal amortisation of `total_debt`),
  discretionary surplus, max new annual debt service at DSCR 1.25/1.50, and — if a proposed instalment
  is supplied — `dscr_on_proposed` + verdict (affordable / marginal / unaffordable). Carries
  `engine_version`, `schema_version`, `generated_at`, `method`, NCA framing. Stamp into the audit
  chain via `append_audit` (type `affordability_assessment`). Pure; finite-guarded; never fatal.
- **Wire:** `report["affordability"]` in `main.py` (next to `lender_view`); `GET /api/report/{id}/affordability`.
- **Tests:** positive/negative EBITDA, missing figures, proposed-instalment verdict bands, hostile/None, JSON-safe.

## 2. Applicant-facing adverse-action reason letter (H3/D2) — exporter
- **Why:** the "why this score" panel exists on screen + PDF/HTML; make it a *portable artifact the SME
  receives* (ECOA/NCA s62 adverse-action shape; POPIA s71 explanation+contestation in one document).
- **Build:** `services/reason_letter.py::build_reason_letter(report)` assembling from `reason_codes` +
  `build_disclosure` (principal reasons, strengths, rights, contestation route, decision-support
  disclaimer); render via existing `report_generator` (PDF) + `html_report` (HTML) helpers. No new math.
- **Wire:** `GET /api/report/{id}/reason-letter.pdf` + `.html`; optional button in `ScoreReasons.jsx`.
- **Tests:** renders with/without components, injection-escaped, no-op when no score, hostile ledger.

## 3. Disparate-impact / 80%-rule fairness metric (H1) — `services/fairness.py`
- **Why:** the one harm honestly *deferred* in the model card. Make it a real, surfaced number now.
- **Build:** `disparate_impact(rows, group_key)` over `recent_reports()`-shaped data → per-group
  selection ratio (favourable = band A–C / score≥threshold), the **80%-rule** ratio (min/max group
  selection rate), and mean-score gap; across the proxies already captured (`industry`, `region/country`).
  Honest: needs a minimum N per group else `insufficient_data`. Slots into `model_card` fairness block.
- **Wire:** `GET /api/admin/fairness`; fairness block in `model_card`.
- **Tests:** clean parity vs biased fixture, small-N guard, missing group, hostile.

## 4. Validation-harness completion (E5 + C1) — `validation.py` + outcomes flag
- **Build:** `psi(expected_bands, actual_bands)` (population stability index) + a realised-vs-predicted
  helper in `validation.py`; a first-class `shadow` boolean on recorded outcomes so shadow runs filter
  distinctly in `/api/admin/validation`.
- **Tests:** PSI = 0 on identical, rises on shift; shadow filter.

## 5. Invariant locks + bottom-up SOM (H4 / D3 / M1)
- Regression test: `imara_components` never contains an owner/personal-credit label (locks H4).
- Regression test: every public report + export payload carries the `decision_support` shield (locks D3).
- `docs/gtm/IMARA_SOM_2026.md`: bottom-up serviceable-obtainable-market (reachable SA lenders +
  accountant-channel partners × pilot→paid conversion × ACV), gap quoted only as context with vintage (M1).

## 6. Alt-data overlay (M2) — `services/altdata_signals.py` (the one genuinely missing capability)
- **Why:** thin/no-file informal firms currently fall through to `available:False`.
- **Build:** ingest a mobile-money / POS-settlement statement via the existing upload+parse path; emit a
  thin-file `altdata_health_score` analogous to `bank_health_score`, surfaced as an **overlay** (not an
  Imara Score input). Phase this after 1–5; larger, but still no partner needed.
- **Tests:** parse a sample MoMo/POS statement, degrade safely, never feeds the Score.

## Activation (Ruan, minutes, near-zero code)
Set `SENTRY_DSN` + `BACKUP_ENABLED` (+ a second backup mount) → flips observability + error-tracking +
DB backups live (O2). Promote `pip-audit`/`npm audit` to blocking at `--audit-level=high` (O3).
