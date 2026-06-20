# Imara Score™ — Model Card
*Governance "nutrition label." Machine-readable mirror: `GET /api/v1/model-card`. As of 2026-06.*

## Summary
A 0–100 bankability / investability rating for South African SMEs, produced by a deterministic
financial engine plus LLM specialist agents, framed as **decision-support** for lenders and investors.

## Intended use
Supports a registered credit provider's own **NCA affordability assessment** and a human analyst's
judgement. **A person makes the final credit decision.** It is *not* a credit score, a creditworthiness
determination, or a lending decision.

### Out of scope
- Consumer (individual) credit scoring.
- An automated lending decision or creditworthiness determination.
- Use without a human credit analyst, or outside an NCA affordability assessment.
- Markets/sectors outside SA SMEs without re-validation.

## Method
Deterministic-first: figures and ratios are computed by arithmetic; LLM agents narrate and flag but
never invent numbers; figures are cross-checked (faithfulness). The Score is a weighted composite of up
to 8 components, re-normalised over those produced.

**Weights are AHP-derived, not ad hoc.** An expert pairwise-comparison matrix (Saaty 1–9) yields the
component priorities with a **Consistency Ratio of 0.0036** (well under the 0.10 threshold). Production
weights are those priorities rounded to clean values:

| Component | AHP-derived | Production |
|---|---|---|
| Profitability | 0.262 | 0.25 |
| Credit Readiness | 0.195 | 0.20 |
| Risk & Compliance | 0.166 | 0.15 |
| Operational Efficiency | 0.093 | 0.10 |
| Financial Integrity | 0.093 | 0.10 |
| Market Visibility | 0.093 | 0.10 |
| Tax Compliance | 0.049 | 0.05 |
| Legal Compliance | 0.049 | 0.05 |

**External validity anchor.** The **Altman Z″-score (emerging markets)** — a published, validated,
purely-deterministic distress model — is computed independently from the firm's balance sheet and
cross-checked against the Imara band (convergent validity). It is *not* a Score component.

**Explainability.** Deterministic reason codes disclose the principal factors, ordered by impact.

## Evaluation
- **Deterministic golden set:** 12/12 ratio cases correct by independent formulas (CI gate).
- **LLM-judge agreement:** 100% with human labels on clear-cut findings (target 75–90%; borderline labels to be added).
- **External convergence:** Z″ distress zone vs Imara band reported per analysis.
- **Online monitoring:** Fleet Quality drift monitor over persisted analyses.

## Fairness
- **B-BBEE status (race-linked) is excluded from the Score** and treated as informational / commercial
  context only — a firm's ownership profile can never lower its bankability rating.
- Industry and region carry indirect signal and are monitored. Alternative-data inputs (e.g. bank
  statements) are surfaced as decision-support, not silent Score inputs.
- Formal disparate-impact testing is deferred until enough real outcomes accumulate (needs labelled data).

## Limitations
- Weights are AHP/expert-derived and the LLM components are **not yet calibrated against real
  funding/repayment outcomes** — a structured heuristic, not an empirically-fitted PD model.
- Thin-file inputs (P&L only, no balance sheet) reduce coverage; Z″ then reports "needs balance sheet."
- LLM narrative can err; mitigated by deterministic numbers + faithfulness cross-check + finding-quality critique.

## Governance (NCA / POPIA)
Not a substitute for the NCA (Act 34 of 2005, s78–81) pre-agreement affordability assessment; does not
authorise lending and must not enable reckless credit (s80). Processes client-provided business/financial
data; figures are extracted deterministically and shown with their source (POPIA, Act 4 of 2013).
Human-in-the-loop required.
