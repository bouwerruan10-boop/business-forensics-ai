# Imara Action Simulator — Implementation Plan
*From "know where you stand" to "know what to do, what it's worth, and how likely it is." Deterministic, traceable, honest — the same DNA as the ratio engine and faithfulness layer.*

## Approach (research-backed)
Industry best practice for this is a **driver-based scenario model**: define the few variables that actually move results, link them to integrated financials, and run a small set of named scenarios (Base / Upside / Downside) plus ad-hoc what-ifs — typically 20–30 drivers, each tied to an action playbook ([AFP](https://www.financialprofessionals.org/training-resources/resources/articles/details/the-fp-a-role-in-driver-based-modeling), [everworker](https://everworker.ai/blog/driver_based_scenario_modeling_fp_a_financial_decision_automation)). That maps perfectly onto Imara, because the "drivers" and their magnitudes are already computed (ratios vs benchmarks) and the "actions" are already attached to findings.

**Core principle:** the maths is 100% deterministic and lives in a tested service (like `financial_ratios.py`). The LLM never generates numbers — at most it phrases/parameterises an action, shown transparently and editable. Outputs are always labelled indicative.

## What we reuse (already in the stored report)
`financial_figures` (raw line items), `financial_ratios`, `imara_components` (label/value/weight), `financial_fundamentals_score`, `industry_key`, `annual_revenue`, `valuation_mid`. The Imara Score's Profitability component is **60% anchored on `fundamentals_score`**, which is a pure function of the figures — this is what lets us project the Score deterministically.

## Drivers (the few that move SME results)
1. **Gross margin** (±pp) — adjusts COGS.
2. **Revenue growth** (±%) — scales revenue (COGS holds % of revenue).
3. **Price increase** (±%) with **volume elasticity** — price up, volume partly down.
4. **Overheads / opex** (±%).
5. **Debtor days** (−days) — releases cash = days/365 × revenue.
6. **Inventory days** (−days) — releases cash.
Each driver recomputes the income statement + working capital + ratios; 6 drivers is the right MVP size (research: keep it to the strong few).

## Scenarios (capture haircuts)
Actions rarely land at 100%. Three named scenarios applied as a realisation factor on each action's benefit: **Optimistic 100% · Expected 60% · Pessimistic 30%** (base/best/worst per FP&A practice). Phase 2 swaps this for Monte Carlo.

## Phased build
**Phase A — deterministic engine (`services/simulation.py`)** — no API, fully unit-tested:
- `derive_actions(report)` → candidate actions from ratios-vs-benchmark gaps, each grounded in the firm's real numbers (id, label, driver, max magnitude, rationale).
- `apply_actions(figures, ratios, selected, industry_key, scenario)` → projected figures → recompute ratios (`compute_ratios`) → recompute `fundamentals_score` → **estimated projected Imara Score** (update Profitability's fundamentals portion, hold LLM-driven components constant, re-normalise) → cash released, margins, valuation delta.
- Tests: baseline round-trips; each driver moves the right line; scenarios scale; score moves monotonically with improvement.

**Phase B — endpoint** `POST /api/simulate/actions {analysis_id, actions:[{id,intensity}], scenario}` → projected state + deltas. Reads the stored report; old reports degrade gracefully.

**Phase C — frontend `ActionSimulator.jsx`** — upgrade the What-If section: list the derived actions with on/off toggles + intensity sliders, a scenario selector, and a results panel showing baseline → projected for Imara Score/band, net profit & margins, cash released, and valuation, with clear "indicative" framing and a per-action contribution breakdown.

Each phase ships behind a green CI build, the established way.

## The possible future (roadmap beyond MVP)
The market is moving descriptive → predictive → **prescriptive → agentic** ([SR Analytics](https://sranalytics.io/blog/data-and-analytics-trends/), [BluePrism](https://www.blueprism.com/resources/blog/future-ai-agents-trends/)). Imara's path:
1. **What-if → what's-best (optimiser).** Given an effort/cash budget, search the action space for the combination that maximises the Imara Score (or cash, or valuation). Turns the simulator from exploration into a recommendation.
2. **Probabilistic (Monte Carlo).** Replace fixed haircuts with sampled action-effectiveness + market volatility over 1,000+ runs → "72% chance of reaching Band C within 12 months," value-at-risk style downside.
3. **Time-phased trajectory.** Project month-by-month (actions have ramp-up), not just an end state — a animated path of the Score/cash over 12–24 months.
4. **Agentic & continuous.** An agent proposes action bundles, and — as the SME re-uploads fresh statements each quarter — Imara tracks plan-vs-actual and re-optimises. This is the "decision intelligence" end-state: from a one-off report to a living plan.
5. **Benchmarked outcomes / calibration.** As real outcomes accrue, back-test the simulator's predictions to tighten the haircuts and elasticities — the same calibration loop flagged for the Imara Score.

The MVP is deliberately the deterministic, trustworthy floor of that ladder; every later rung adds power without abandoning the traceable core.
