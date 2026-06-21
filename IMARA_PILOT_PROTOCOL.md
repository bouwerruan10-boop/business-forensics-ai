# Imara — Design-Partner Pilot & Calibration Protocol
*The runnable program that converts the perennial "Score is uncalibrated vs outcomes" gap into evidence. Research-grounded (B2B fintech pilot best practice + credit-model validation). As of 2026-06.*

## Why this exists
Imara is engineering-mature but **evidence-immature**: the Imara Score's weights are AHP/expert-derived and not yet validated against real funding/repayment outcomes. The SA SME fintech market now competes on **trust and distribution**, not features — so demonstrated predictive validity is the highest-leverage next asset. This protocol produces it.

## The machinery is already built (use it)
- **Record outcomes:** `POST /api/admin/outcomes` `{analysis_id, outcome_type, label, value, source}` (label 1=bad/default, 0=good).
- **See validation:** `GET /api/admin/validation` — AUC / Gini / KS + a reliability table on real outcomes, **plus a Z″-proxy backtest available now** from existing analyses.
- **See calibration:** `GET /api/admin/calibration` — Platt mapping Score→probability-of-distress once N≥50 (the AHP prior stands until then).

## Pilot design (3 months — the B2B-fintech standard)
**Partner:** one lender or a lending-enabled platform (e.g. an SME lender, or a broker/accountant network that sees outcomes). Imara is **decision-support**, not a lender.

**Before kick-off, agree in writing:**
- **Success = predictive lift vs the partner's current baseline** (their existing score/manual decision), measured by AUC/Gini uplift on the same applicants, **and** willingness-to-pay.
- **Data to collect:** for each applicant — the Imara analysis + the partner's decision (funded/declined) + the eventual outcome (repaid/default/arrears) once seasoned. Request a **labelled historical portfolio sample** up front to backtest immediately.
- **Volume target:** ≥ 50–100 labelled cases with both outcomes (the calibration threshold).
- **Go / kill gates (green-yellow-red on 5 criteria):** predictive lift, calibration quality (Brier), willingness-to-pay, integration effort, partner engagement. Mostly green → commercial step; mixed → extend only on decision-relevant questions; mostly red → stop (don't treat as traction).

## Calibration ladder (cold-start → seasoned)
1. **Now (0 outcomes):** Z″-proxy backtest for convergent validity; AHP weights = the documented expert prior.
2. **Early (a labelled historical sample):** run discrimination on the sample (`/admin/validation`); reject-inference for declined cases.
3. **N ≥ 50 both-class:** Platt calibration → Score→PD (`/admin/calibration`); report Brier + reliability.
4. **Seasoned (≥ 6–12 mo, more outcomes):** refit weights (Bayesian update of the AHP prior), run disparate-impact testing, re-issue the model card with real metrics.

## What "good" looks like
AUC 0.5 = no skill · 0.65–0.70 = usable · 0.75+ = strong · 0.80+ = excellent. Gini = 2·AUC−1. A monotonic reliability table (bad-rate falls as the Score rises) is the headline trust artifact.
