# Imara — Simulator Improvement Plan
*Research-driven (FP&A best practice + Monte-Carlo literature + r/FPandA practitioner sentiment) and grounded in an empirical check of Imara's own simulator on the demo. The Action Simulator is already FP&A-grade; this plan closes four specific, evidence-backed gaps.*

## 0. What the research says a good simulator must do
- **Driver-based "if you do X, you get Y"** — practitioners *prefer* causal driver scenarios over Monte Carlo (management actions are levers, not random variables). ([r/FPandA](https://www.reddit.com/r/FPandA/comments/1qjh774/why_isnt_a_monte_carlo_simulation_popular_and/))
- **Few, high-impact, correctly-chosen drivers**; **always a range, not a point**.
- **Monte-Carlo killers:** treating drivers as **independent** (bands come out too narrow; real correlations even spike under stress), **false precision** (more runs don't fix bad inputs — the distribution *shape/range/correlation* matters more than run count), **outside-history blindness**. ([Kitces](https://www.kitces.com/blog/monte-carlo-correlation-matrix-investment-assumptions-retirement-planning-projection/), [Farseer](https://www.farseer.com/blog/what-is-monte-carlo-analysis-and-how-does-it-work/))
- **Credible, surfaced assumptions** — no hidden hard-coded values. ([FP&A Trends](https://fpa-trends.com/article/driver-based-forecasting-fpa))

## 1. What Imara already does well (keep)
Driver-based; drivers derived from the firm's *own* ratio-vs-benchmark gaps (not generic); 3 realisation scenarios; tornado (`rank_levers`); bundle optimiser (`optimize_actions`); SA-tax realism (27% on incremental operating profit); price–volume elasticity (−0.5); plausibility guards; separate macro stress test. Deterministic, labelled indicative. This is a genuine strength and aligns with best practice — do not rip it out.

## 2. The empirical finding (why this plan exists)
Running `monte_carlo` on the demo (2,000 runs, 4 actions): the **net-profit band is reasonable** (p10 R1.75M / p50 R2.57M / p90 R3.5M) but the **Imara-Score band collapsed to 51 / 52 / 52** (a 1-point spread) with **prob_reach_next_band = 1.0**. That is false precision — a probabilistic readout that tells the user nothing. And the default action magnitudes are the *full* benchmark gap (e.g., a **19.8pp** gross-margin jump as the "default" target) — fantastical for an SME.

## 3. The plan (prioritised)

### Build 1 — Correlated Monte Carlo (shared execution factor)  ★ highest value
**Problem.** `monte_carlo` samples each action's realisation from its *own* triangular and revenue noise from its *own* gaussian — independent. Independent errors cancel, so the downside band is too narrow and the score band collapses.
**Fix.** Per run, draw ONE common **execution-conditions factor** `E` (e.g. `triangular(0.4, 1.0, 0.72)`). Each action's realisation = `clamp(E × idiosyncratic_i)` with a *tight* per-action `idiosyncratic_i ~ triangular(0.8,1.15,1.0)`. Tie the revenue market-noise mean to `(E − centre)` so good conditions lift growth and bad conditions contract it (the systematic-risk correction). Keep it seeded/deterministic.
**Result.** Realistically wider p10–p90, a meaningful (not collapsed) score band, and a `prob_reach_next_band` that isn't a spurious 1.0. Add a "what has to go right" line (the p10 = low-execution world).
**Effort.** Small — contained to `monte_carlo()`. **Verify:** band widens vs the independent version; test asserts real p10<p50<p90 spread and prob<1.0 on the demo.

### Build 2 — Calibrate action magnitudes to a realistic share of the gap  ★ high value
**Problem.** `derive_actions` sets each action's `default` = the *full* gap to benchmark. Closing the entire gap is unrealistic; it makes even the expected case fantastical.
**Fix.** Introduce a realistic close-fraction (default ~0.4 of the gap as the *expected* target; the full gap stays as `max`, reachable via the intensity slider). Per-lever overrides where warranted (e.g. debtor-days closes more easily than gross-margin). 
**Result.** Believable headline projections, not just a believable MC. **Effort.** Small — `derive_actions` magnitudes. **Verify:** `default ≈ fraction × gap ≤ max`; demo projection no longer implies a ~12–20pp margin jump.

### Build 3 — Surface the assumptions
**Problem.** Realisation haircuts (30/60/100%), elasticity (−0.5), tax (27%), and the MC distribution/correlation are hard-coded and invisible.
**Fix.** Add an `assumptions` block to `apply_actions` / `monte_carlo` output (realisation %, elasticity, tax, MC distribution + correlation note, iterations/seed) and show it in `ActionSimulator.jsx` (a small "assumptions" expander). Optionally widen the MC idiosyncratic spread when data confidence is low (few months of bank history / AI-extracted figures).
**Effort.** Small. **Verify:** output carries `assumptions`; frontend renders it.

### Build 4 — Time-phased 12-month trajectory (bigger, later)
**Problem.** Single-period steady-state — no ramp, no cash-timing (the "profitable but broke" story needs a path).
**Fix.** Actions ramp to full effect over N months (S-curve); project monthly revenue/profit/cash via `_project` with a ramp multiplier; return ~12 points + the month cash turns positive. New `project_trajectory()` + endpoint + a frontend line chart.
**Effort.** Medium. **Verify:** monotonic ramp; 12 points; cash path.

## 4. Sequencing & guardrails
Do **Build 1 + Build 2 together** (core realism), then **Build 3** (cheap transparency), then **Build 4** (strategic, bigger). All stay deterministic (no LLM in the numbers), labelled indicative, and are decision-support — not guarantees, not an Imara Score change. Honest framing to add: the action Monte Carlo models *execution* variance, not external shocks — point users to the macro stress test for shocks (covers the outside-history pitfall).
