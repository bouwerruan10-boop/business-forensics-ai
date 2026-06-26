# Tax Me If You Can — input/UI research: getting a better outcome from better inputs

Analysed 2026-06-24. Goal: what should the **inputs** to the Tax planner be, so the agent produces the most accurate, personalised, decision-useful result. Grounded in the current SA residency/exit-tax rules and in how the engine actually consumes the inputs.

## A. What the UI collects today (`TaxPlanner.jsx`)
1. **Income types** — 7 chips (employment, business, dividends, interest, rental, capital gains, pension).
2. **Annual amounts** — optional bare `type=number` field per selected type ("enables quantified saving").
3. **Destinations** — 8 corridor chips (AE, CY, PT, MU, MT, GR, IT, CH); none = all.
4. **Worldwide assets** — a single *market value* + *base cost* (for the s9H exit-CGT estimate).
Origin is hard-set to ZA. That's the whole input surface.

## B. What the engine does with them — and the accuracy gaps (the real story)
- **`_sa_current_tax()` is GROSS.** It sums ordinary income → income-tax tables, adds 20% on dividends and the effective CGT on capital gains. It does **not** apply: age rebates, the annual interest exemption, the CGT annual exclusion, or any existing deductions (RA, medical, donations). → the "indicative current SA tax" baseline is **overstated**, so every destination's **"indicative saving ≈ R…/yr" headline is inflated.** This is the single biggest credibility risk in the tool.
- **Exit CGT lumps everything.** The single "worldwide market value" is run through 40% × 18%. But **s9H deems disposal of worldwide assets EXCLUDING SA immovable property, retirement-fund interests, and personal-use assets/cash** (sourced). Feeding one lumped figure **overstates the exit charge**.
- **No personalisation.** Corridor "fit" keys off income mix only — not age, family, intent, or days abroad — so two very different people get the same ranking.

> Net: the inputs are thin, and the two numbers a user actually reads — the **saving** and the **exit tax** — are both systematically too high. Fixing the inputs that feed these is higher-leverage than adding more corridors.

## C. Research-grounded input improvements (prioritised)

### P0 — make the headline numbers honest (accuracy)
1. **Age band (<65 / 65–74 / 75+).** Drives the primary/secondary/tertiary **rebates** (R17,820 / +R9,765 / +R3,249 2025/26), the higher **interest exemption** (R34,500 vs R23,800 at 65+), and medical credits — so the baseline is realistic. *Engine: `_sa_current_tax(income, age)`.* Also personalises which levers lead (retiree vs earner).
2. **Existing deductions already claimed** — RA/pension contribution (R or % of income), medical-scheme members, annual s18A donations. Subtract these before computing the baseline so the saving is **net-of-what-they-already-do**, not a phantom gross gap. *Engine: net taxable income.*
3. **Asset breakdown for exit tax** — replace the single field with three buckets: **SA immovable property** (excluded from s9H), **retirement-fund value** (excluded), and **other worldwide assets** + base cost (the only bucket deemed disposed). Optionally a **primary-residence value** (R2m CGT exclusion). *Engine: tax only the "other" bucket.* Removes the over-statement.

### P1 — personalisation + corridor fit
4. **Days spent / intended outside SA per 12 months.** Flags the **s10(1)(o)(ii)** foreign-employment exemption (needs >183 days incl a 60-day continuous block; first R1.25m exempt) and the residency-cessation picture (physical-presence test; 330 continuous days out). *Engine: gate the foreign-employment lever + a residency-status read.*
5. **Foreign tax already paid** (total or per stream). Powers the **s6quat** double-tax credit in the comparison so "relocate" vs "stay" is apples-to-apples.
6. **Goal selector** — *stay & optimise* / *relocate permanently* / *work abroad temporarily*. Leads with the relevant half of the output and re-ranks corridors. Cheap, big clarity win.
7. **Dependants + medical-scheme members.** Medical credits in the baseline; plus a DTA "centre-of-vital-interests" note for dual-residence tie-breaks.

### P2 — input quality / UX of the existing fields
8. **Income amounts:** a monthly⇄annual toggle, live R-formatting with thousands separators, and clarifying helper text ("annual, before deductions"). Bare number fields invite order-of-magnitude errors that swing the whole result.
9. **Destinations:** a one-line "suits whom" hint per corridor (rate-based vs flat-fee, and that flat-fee regimes only pay off at high income) so the choice is informed, not blind.
10. **Validation + friendly errors + a "not sure?" path** — leaving amounts blank should still give the qualitative landscape (it does) and say so.
11. **Presets + save/share a scenario** — e.g. "retiree: pension + rental", "owner-operator", "remote employee abroad"; let the operator save/re-run a client scenario (mirrors the rest of Imara's operator workflow).

## D. Recommendation
Do **P0 first** — it's the difference between a number a client can trust and one a tax practitioner will tear apart. The inputs to add (age, existing deductions, asset breakdown) are small UI additions but each requires a matching engine tweak so the baseline and exit charge are computed *net* and *exclusion-aware*. P1 (days abroad, foreign tax paid, goal selector) turns it from a generic table into a personalised plan. P2 is polish that reduces "garbage-in".

**Effort map:** P0 #1–#3 = UI field + a focused `_sa_current_tax`/exit-CGT change each + tests. P1 #4–#7 = UI + light engine gating. P2 = UI-only.

*All of this stays within the existing guardrails — factual decision-support, not advice; better inputs make the hand-off to a licensed practitioner sharper, not the tool more "advisory".*

Sources: SARS physical-presence & cease-residency; PwC/Shepstone & Wylie on s9H exit-tax exclusions (SA immovable property + retirement funds excluded); SARS s10(1)(o)(ii) foreign-employment (183/60 days, R1.25m); SARS/PwC 2025/26 rebates & thresholds.

## Update — P0 + key P1 implemented (2026-06-24, v1.91)

- **P0 accuracy — DONE.** `_sa_current_tax(income, age, deductions)` now applies the age-tiered **interest exemption** (R23,800/R34,500), the **CGT annual exclusion** (R40,000), **age rebates** (secondary R9,444 / tertiary R3,145 on top of the primary), and **existing deductions** (retirement contribution capped s11F, s18A donations capped 10%, medical-scheme members → s6A credits). Baseline is now NET, not gross. Exit-CGT now takes an **asset breakdown** and charges only the "other worldwide" bucket — **SA immovable property, retirement funds and primary residence are excluded** (s9H). Legacy single `worldwide_market_value` still works.
- **P1 — DONE (key items):** `goal` selector (stay/relocate/work_abroad), `days_abroad` (drives a residency note flagging the s10(1)(o)(ii) >183/60-day foreign-employment exemption), echoes of age/deductions/goal in the output.
- **UI:** `TaxPlanner.jsx` exposes goal, age, days-abroad, existing-deductions, and the 5-field asset breakdown, plus a **monthly⇄annual** amount toggle and a retry on error. Renders the residency note + exit-exclusions.
- Verified: 453 pytest pass (+3), endpoint pressure (full profile + 10 hostile bodies 0×5xx + 413 body-cap), vite build clean. Backward-compatible; not-advice/GAAR framing unchanged. **#4 foreign-tax-paid baseline credit and P2 presets/save-scenario remain future.**
