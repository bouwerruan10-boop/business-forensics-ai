# Feasibility: an Action-Outcome Simulation for Imara
*Analysis only — no implementation. Question: can Imara take the analytics a user receives and simulate the possible outcomes of the actions available to them?*

## Short answer
**Yes — and it's arguably the single most natural, high-differentiation feature Imara could add.** The reason is unusual: the hardest part of building a prescriptive simulation is normally *getting clean, structured inputs and quantified actions*. Imara's pipeline already produces all of them. This would be an *extension of existing components*, not a new data-gathering problem.

## What the idea actually is (named)
It's **prescriptive analytics** — the fourth analytics tier on top of what Imara already does:
- Descriptive ("what is true") → the findings.
- Diagnostic ("why") → root causes / SCR narrative.
- Predictive ("what's likely") → the bull/base/bear forecast.
- **Prescriptive ("what happens if I act, and what's best") → the proposed simulation.**
Industry framing: prescriptive analytics "simulates the likely outcome of each possible action and recommends the one that leads to the best result," elevating scenario planning from *"what if?"* to *"what's best?"* ([Amplitude](https://amplitude.com/explore/analytics/what-prescriptive-analytics), [Aziro](https://www.aziro.com/en/blog/prescriptive-analytics-definition-tools-and-techniques-for-better-decision-making)).

## Why Imara is unusually ready for it (the inputs already exist)
1. **A deterministic financial baseline.** `services/financial_ratios.py` already extracts `financial_figures` (revenue, COGS, opex, receivables, payables, equity, debt, …) and computes `financial_ratios` by arithmetic. That is exactly the starting state a simulation perturbs.
2. **Quantified, actionable "levers" — already attached to every finding.** Each `AgentFinding` carries `financial_impact` (e.g. "R 3.4M annual margin leakage"), `roi_estimate`, `cost_of_inaction`, a one-line `recommendation`, and a `quick_win` flag. These ARE the candidate actions, each with a magnitude and a timeframe already estimated.
3. **A scoring function that can be re-run.** `CEOAgent._calculate_imara_score` can recompute the Imara Score/band from a *modified* financial state, so the simulation can show "do these actions → Score 49 (Band D) climbs to 63 (Band C)."
4. **Forecast + valuation models** (bull/base/bear, valuation_mid) to project the resulting revenue path and value.
5. **A working simulator pattern to build on.** `/api/simulate` + `digital_twin_parameters` already exist end-to-end (frontend `Simulator.jsx` → backend) — proof the plumbing works.

## The gap (today's simulator vs the idea)
The current What-If simulator is **single-variable, single-period, benchmark-ratio based** ("Revenue +5% → profit impact at the industry operating margin"). It does **not**: use the firm's actual extracted figures, draw on the findings/recommendations, combine multiple actions, project over time, or recompute the Score/valuation. The idea needs all five.

## Recommended approach (keeps Imara's anti-hallucination DNA)
**Core = a deterministic, driver-based projection** — the same philosophy as the ratio engine, so the numbers stay traceable and no LLM invents figures:
- Start from the real `financial_figures`.
- Represent each action as a parameterised change to a **driver**: COGS %, debtor days, opex, price, volume, headcount cost, etc. (e.g. "renegotiate suppliers" → "COGS −3pp phased over 90 days").
- Recompute the income statement, working-capital/cash, ratios, **Imara Score**, and valuation deterministically after applying the selected actions.
- Let the user **toggle actions on/off** and see the combined projected state and a 12–24 month trajectory.

**Where the LLM helps (safely):** only to *parameterise* fuzzy recommendations into driver deltas (and to phrase them) — shown transparently and **editable**; the arithmetic is never LLM-generated. This mirrors the existing faithfulness/extraction split.

**Handling uncertainty (phase 2): Monte Carlo.** Sample each action's *realised* effectiveness (actions rarely land at 100%) plus external volatility, run 1,000+ iterations, and output a distribution: "70% chance of reaching Band C within 12 months," value-at-risk style ranges. Research is clear this is powerful **but only as good as its assumptions** — favour a "simpler model with strong drivers and clear distributions" over false precision ([Empire Westcorp](https://www.empirewestcorp.com/monte-carlo-business-simulation-assessing-financial-risk-by-modelling-thousands-of-possible-outcomes/), [Farseer](https://www.farseer.com/blog/what-is-monte-carlo-analysis-and-how-does-it-work/)). Start deterministic (best/expected/worst via capture haircuts, e.g. 100/60/30%); add Monte Carlo later.

## Outputs it could produce
- Projected P&L + cash trajectory under the chosen actions.
- New **Imara Score / band** and which components moved.
- Valuation uplift and time-to-impact per action.
- A **prescriptive ranking**: best "bang-for-buck" actions (largest Score/cash gain per effort or cost), i.e. "what's best," not just "what if."

## Risks & how to keep it credible
- **Compounding/overstatement** when stacking actions → apply realisation haircuts, diminishing returns, and stack effects on drivers (not naive addition of rand impacts).
- **Second-order effects** (price↑ usually → volume↓) → model paired levers/elasticities for the few that matter; don't pretend independence everywhere.
- **Framing** → label everything indicative/estimate (consistent with the Methodology & Confidence panel already shipped); never present simulated valuations as guaranteed, especially for lenders.
- **Determinism** → keep all maths in a tested service (like `financial_ratios.py` / the eval harness), LLM out of the numbers.

## Verdict & rough shape
**Feasible and high-value.** It reinforces the core promise — from *"know where you stand"* to *"know what to do, what it's worth, and what's most likely."* Indicative effort:
- **MVP:** a deterministic multi-action projector (reuse `financial_figures` + Score recompute + a findings→driver map) surfaced as an upgraded "Action Simulator" replacing/augmenting today's What-If panel. Medium build, low data risk.
- **Phase 2:** Monte Carlo ranges + an optimiser ("best combination of actions under a time/effort/cash budget").

No blockers identified. The main design discipline is keeping the simulation arithmetic deterministic and the assumptions visible/editable — which is exactly the pattern Imara already follows.
