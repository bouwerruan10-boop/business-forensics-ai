# Imara Score™ — Model Development & Conceptual-Soundness Dossier

**Status:** pilot collateral (v1, 2026-06-28). **Positioning, stated up front and without hedging:** the Imara Score is a **decision-support / bankability-triage** rating. It has **not** been calibrated against real funding/repayment outcomes and is **not** a statistically-validated default-prediction model. This document is the *conceptual-soundness* evidence (the SR 11-7 first pillar) that supports running the Score in a **shadow-mode pilot** — it is not a claim of statistical validation. The live, per-firm version of this pack is the `GET /api/report/{id}/evidence-pack` endpoint (`services/evidence_pack.py`).

> Why this framing: the strategic research (`docs/research/IMARA_STRATEGIC_RESEARCH_2026-06.md`, Thread 1) found that a judgmental/expert-weighted score is defensible *as triage*, but buyers ultimately require outcome analysis before it drives decisions. Leading with "validated" claims we cannot yet support invites the exact credibility attack a sophisticated lender will make. So we lead with conceptual soundness + benchmark convergence + an honest roadmap.

---

## 1. What the Score is

A single branded **0–100 bankability / investability rating**, banded:

| Band | Range | Label |
|---|---|---|
| A | 80–100 | Investment Ready |
| B | 65–79 | Bankable |
| C | 50–64 | Developing |
| D | 35–49 | At Risk |
| E | 0–34 | Distressed |

It is produced by `agents/ceo_agent.py::_calculate_imara_score()` from the deterministic component scores already computed earlier in the pipeline.

---

## 2. The component model and weights (the "underlying logic")

The Score is a **weighted blend of up to 8 components**, each itself a 0–100 sub-score (higher = better). The base weights below are an **expert/AHP prior** — they encode what a lender or investor weights, with profitability and credit readiness dominant:

| Component | Base weight | What it measures | Source |
|---|---|---|---|
| Profitability | 0.25 | Margins/earnings quality (60/40 blend of **computed fundamentals** and agent assessment) | `financial_ratios.py` + FinancialAgent |
| Credit Readiness | 0.20 | Lender creditworthiness | Credit Readiness Agent |
| Risk & Compliance | 0.15 | Aggregate risk findings | cross-agent |
| Operational Efficiency | 0.10 | Working-capital / throughput | Operations Agent |
| Financial Integrity | 0.10 | `100 − fraud_risk_score` | Fraud & Anomaly Agent |
| Market Visibility | 0.10 | Market presence | Market Research Agent |
| Tax Compliance | 0.05 | `100 − SA tax risk` | SA Tax Agent |
| Legal Compliance | 0.05 | `100 − SA legal risk` | SA Legal Agent |

**Computation (fully deterministic, no LLM):**
- Components not produced this run are **dropped** and the remaining weights **re-normalised**, so the Score is always 0–100 (`composite = Σ(value × weight) / Σ(weight)`).
- The biggest component (Profitability) is **anchored on computed fundamentals** (real margins) rather than LLM finding-count — a deliberate de-biasing.
- A **data-completeness / confidence** signal is published alongside every Score: of the 8 possible components, how many were produced (`imara_completeness` %, `imara_confidence` = high/medium/low). A thin score never looks as solid as a full one.
- The per-analysis re-normalised weights and each component's **point contribution** (`value × weight`) are exposed via `services/score_disclosure.py` — see §5.

---

## 3. Anti-hallucination architecture (why the numbers are trustworthy)

Imara is **deterministic-first**: every figure — ratios, scores, projections, thresholds, tax — is computed in pure, unit-tested functions under `backend/services/`. The LLM agents **narrate and prioritise; they never invent a number.** Two verifiers cross-check the narration against the computed source and fail closed on a mismatch:
- `services/faithfulness.py` — guards the numbers in prose against the computed set.
- `services/prose_verifier.py` — flags qualitative narrative that contradicts the computed ratios or a corroborated cross-agent finding.

This is the architecture the 2025–2026 trustworthy-AI consensus converges on (deterministic calc engine + grounded narration + verification). It is *how Imara earns the right to be believed*, independent of Score validation.

---

## 4. Benchmark convergence — the independent Altman Z'' cross-check

Before any outcome data exists, the highest-credibility evidence is **convergence with an established benchmark.** `services/distress_score.py::altman_z_em()` computes **Altman's Z''-score (EM-score)** — purpose-built for non-manufacturing, privately-held, emerging-market firms — and compares its distress zone to the Imara band:

| Z'' zone | Threshold |
|---|---|
| Safe | > 2.60 |
| Grey | 2.10 – 2.60 |
| Distress | < 2.10 |

When the independent Z'' zone and the Imara band agree, that is **convergent validity** — evidence the Score reads the firm the way a 50-year-validated model does. When they diverge, the divergence is surfaced and explained. This is shipped and runs on every analysis with sufficient financials.

---

## 5. Explainability & contestability (regulatory-grade)

- **Factor attribution (NCA s62 / FSCA SHAP-LIME-equivalent):** `services/reason_codes.py` lists the principal reasons the Score isn't higher, ordered by impact (`weight × (100 − value)` — the real model math), each tied to the concrete underlying number.
- **POPIA s71(3) disclosure:** `services/score_disclosure.py::build_disclosure()` packages the underlying logic (per-component contribution), the principal reasons, which inputs were used vs not, and the data subject's rights.
- **Contestability (POPIA s71(3) "make representations"):** a data subject can contest the Score or any factor; the representation is recorded **immutably in a tamper-evident hash chain** (`decision_audit`) and reviewed by a human.

---

## 6. Audit trail (examination-survivable)

Tax and decision figures can be written to a **tamper-evident, hash-chained audit log** (`services/database.py::append_audit` / `verify_audit_chain`). For tax specifically, `services/tax_audit_trail.py` cites the **exact statutory provision** and dated rate source behind every figure, so an auditor or SARS can reproduce it. "We can prove how every number was derived" is a claim general-purpose copilots cannot make.

---

## 7. Calibration — honest cold-start

`services/score_calibration.py` implements Platt scaling but **reports "not calibrated" until N ≥ 50 labelled outcomes** — it does not manufacture a probability of default from zero data. `services/validation.py` computes AUC / Gini / KS / reliability the moment real outcome pairs exist. The harness is built and idle by design; it is waiting for outcomes, not pretending to have them.

---

## 8. Outcome-validation roadmap (the path to "validated")

The Score becomes a *validated* model only via real outcomes. The plan, and the targets buyers expect:

- **Method:** run the Score in **shadow / champion-challenger mode** on a design-partner lender's book — score live applicants alongside the lender's existing decision, change nothing, capture both. This is the industry-standard safe way to test a new credit model and the only thing that produces a true Gini/KS.
- **Targets (practitioner conventions, research-confirmed):** Gini **> 0.40**, AUC **> 0.70**, KS **> 0.25**; stability PSI **< 0.10**; calibration Hosmer–Lemeshow p **> 0.05**; sample trending toward **~1,500 goods + ~2,000 bads** over a **12-month** performance window to a defined default (e.g. 90+ DPD).
- **Until then:** the four-pillar minimum-viable-evidence status is reported live in the evidence pack — conceptual soundness (documented), benchmark convergence (Z''), expert-panel agreement (to run), outcome validation (cold-start).

---

## 9. Governance, fairness, limitations, regulatory posture

- **Model card:** `services/model_card.py` (intended use, out-of-scope, method, evaluation, fairness, limitations, governance).
- **Fairness:** the Score must not proxy prohibited grounds; bias testing is part of the outcome-validation phase (FSCA Nov-2025 AI report expectation). Documented as a commitment, not yet a measured result.
- **Limitations:** uncalibrated heuristic; quality depends on input completeness (hence the published confidence signal); SA-focused.
- **Regulatory posture (`docs/research/IMARA_STRATEGIC_RESEARCH_2026-06.md`, Thread 3):** Imara is **decision-support**, not a credit provider or credit bureau (it analyses the client's own data and does not warehouse-and-resell a credit database). POPIA s71 is satisfied because **a human makes any actual lending decision** (the Score is not "based solely" on automated processing), backed by the explainability + contestability above.

---

*This dossier is decision-support collateral, not tax/legal/credit advice. It documents conceptual soundness for a shadow-mode pilot; it does not assert statistical validation, which is contingent on the outcome data the pilot is designed to produce.*
