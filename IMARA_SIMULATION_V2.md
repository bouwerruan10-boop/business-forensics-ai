# Action Simulator v2 — self-analysis, research, Q&A, and improvement plan
*Cycle: analyse what I built → research how simulators are made/validated → ask myself questions → answer them → plan → execute.*

## 1. What I actually built (honest analysis)
The v1 engine is a **deterministic, driver-based, single-period point estimate**. `derive_actions` reads the firm's ratio-vs-benchmark gaps and exposes levers (margin, overheads, debtor/inventory days, growth, price). `apply_actions` applies them as driver deltas, recomputes the income statement + working capital + ratios + `fundamentals_score`, and projects the Imara Score by moving Profitability's 0.6 fundamentals anchor. Three scenario haircuts (30/60/100%) and a per-action intensity. It is well-verified (unit tests for no-op, improvement, monotonicity) and grounded (no LLM in the numbers).

**Blind spots I can see:**
1. **No uncertainty** — it returns single numbers, not a probability of outcomes. This is the biggest gap.
2. **No "what's best"** — pure what-if; it never ranks which lever matters most.
3. **Naive stacking & no plausibility guards** — drivers can in principle push to implausible states.
4. **No tax** — net used operating − interest; incremental profit wasn't taxed, and the model baseline net didn't equal the report's actual net.
5. **Static** — an end-state, not a trajectory over time (actions ramp up).

## 2. Research — how simulators are made & validated
- **Three paradigms** ([Oxmaint](https://community.oxmaint.com/discussion-forum/monte-carlo-vs-discrete-event-simulation-key-differences-and-applications), [AWS](https://aws.amazon.com/what-is/monte-carlo-simulation/)): **Monte Carlo** (random inputs → *probability* of each outcome), **discrete-event** (sequences of state changes), **system dynamics** (stocks/flows/feedback over time). Mine is a degenerate spreadsheet model; the right upgrade for blind-spot #1 is **Monte Carlo**, and for #5 is a system-dynamics-style monthly trajectory.
- **Verification & Validation is a formal discipline** ([Sargent/WSC](https://www.informs-sim.org/wsc97papers/0053.PDF), [LANL](https://www.osti.gov/servlets/purl/835920)): *verification* = the model is built correctly (mathematical **sanity checks**, e.g. known-input→known-output, and **convergence** — run enough iterations until the statistics stabilise); *validation* = it represents reality (calibrate against outcomes). Document assumptions; passing sub-tests ≠ overall credibility.
- **Sensitivity / tornado analysis** ([Wikipedia](https://en.wikipedia.org/wiki/Tornado_diagram), [CFO Perspective](https://cfoperspective.com/tornado-diagrams-to-find-the-risks-and-opportunities-of-your-plan/)): vary one driver at a time and rank by impact — the longest bar is the biggest lever. Cheap, high-value, and turns the tool prescriptive.

## 3. Questions I asked myself — and the answers
- **Q. Which blind spot is most worth fixing first?** Uncertainty. A single projected number reads as a promise; a *distribution* ("≈70% chance of reaching Band C") is both more honest and more useful. → Build **Monte Carlo**.
- **Q. How do I keep Monte Carlo honest, reproducible, testable?** Seed the RNG (deterministic tests); run ≥1,000 iterations (convergence, per research); sample each action's *realisation* from a triangular(0.3, 0.6, 1.0) distribution that reuses the existing scenario anchors; add small market noise on revenue; report p10/p50/p90 and P(reach next band). Label clearly.
- **Q. Is my Score-uplift too narrow (margin only)?** **No** — verified that `fundamentals_score` already blends margin, current ratio, gearing, debtor days and interest coverage, so working-capital and gearing actions already flow into the Score correctly. Per V&V, I must **not** invent extra component couplings I can't justify.
- **Q. How do I raise credibility cheaply (V&V)?** Add **plausibility guards** (COGS can't fall below a floor, no negative figures, sane margins), **diminishing returns** so stacked margin levers can't overshoot, and **tax realism** (apply SA company tax to incremental profit; set baseline net = the report's actual net so it matches the dashboard).
- **Q. Can I add prescriptive value now?** Yes — a **tornado/sensitivity ranking** of each action's standalone Score + profit impact ("biggest levers"), reusing `apply_actions`.
- **Q. What's genuinely deferred?** A **time-phased trajectory** (monthly stocks/flows with ramp-up), an **optimiser** (best bundle under an effort/cash budget), **calibration** against real outcomes, and **saved/named scenarios**.

## 4. Plan (this cycle — deterministic, tested, grounded)
**Engine (`services/simulation.py`):**
1. **Tax realism & baseline consistency** — `TAX_RATE` applied to the incremental operating profit; baseline net = report's actual net.
2. **Plausibility guards** — clamp COGS/opex/margins to sane bounds so no scenario yields absurd states (a verification sanity check).
3. **`rank_levers(report, scenario)`** — standalone Score/profit/cash impact of each action, sorted → tornado data.
4. **`monte_carlo(report, selected, n=1000, seed)`** — sampled realisation + revenue noise → p10/p50/p90 of net-profit delta and projected Imara Score, plus **P(reach next band)**. Seeded and convergence-sized.
**Endpoints:** `GET /api/report/{id}/levers`, `POST /api/simulate/montecarlo`.
**Frontend:** a "Biggest levers" ranked strip and a "Likelihood" readout (probability of reaching the next band, with a p10–p90 range) added to the Action Simulator.
**Tests:** lever ranking order; Monte Carlo determinism (same seed → same stats), p10≤p50≤p90, probability in [0,1]; tax reduces net delta vs pre-tax; plausibility never produces negative/absurd figures.

Everything ships behind a green CI build, the established way. The deferred items (trajectory, optimiser, calibration) are the next rungs on the descriptive→predictive→prescriptive→agentic ladder.
