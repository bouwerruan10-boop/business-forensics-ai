# "Tax Me If You Can" — Extensive Research Brief

**Date:** 21 June 2026
**Status:** FLAGSHIP top-priority initiative (Ruan-directed). Distinct product from Imara, but built on Imara's deterministic-first engine + DNA.
**Important framing:** this brief is built around the **legal, compliant** product — *tax efficiency + relocation planning*, not "loophole"/evasion. The legal guardrails aren't an obstacle; they're the moat (they're what most competitors get wrong). I am not a tax lawyer; this is a factual landscape + build plan, not advice.

---

## 1. Verdict (read this first)

**Real, large, and genuinely underserved — IF built as a compliant, deterministic, professionally-supervised platform.** The "find every loophole + mass-migrate people for tax" framing is a legal liability and should be **reframed** to *"legally minimise your tax and relocate, with licensed sign-off."* Do that, and you have a defensible business in a $30–100B market with a clear white-space and an architecture Imara already owns.

The single biggest strategic insight: **tax is the textbook case for Imara's deterministic-first + human-in-the-loop DNA.** AI-reliability research is unanimous — pure-LLM tax advice hallucinates and compounds (a 5-step chain at 90%/step is only 59% reliable); the production pattern (EY runs 150 agents but professionals keep final sign-off) is *deterministic rule engine + LLM narration + licensed-advisor sign-off*. That is exactly Imara's engine. So this isn't a from-scratch build — it's Imara's IP pointed at a new, larger market.

---

## 2. Market size (large, growing)

- **Tax advisory services:** ~$34.6B (2021) → **~$97.1B (2031)**, ~11% CAGR.
- **Tax tech:** ~$23.4B (2026) → **~$60.7B (2034)**, ~12.6% CAGR.
- **AI-in-tax-advisory:** ~$2.95B (2024) and growing fast; 34% of tax firms already use genAI, +47% planning to.
- **Wealth migration:** a record **~142,000 millionaires** projected to relocate in 2025; Henley & Partners alone has channelled **$15B+ in FDI** across 47 programmes; **tax treatment is the #1 relocation driver.**

---

## 3. The white-space (who we serve, and why incumbents miss them)

The decisive finding: **mass-affluent / higher-earning remote workers, expat entrepreneurs, and online-business owners are deeply confused about "where am I tax resident?"** — 183-day rules, FEIE pitfalls, "your visa doesn't exempt you," business-presence triggers — but they **sit between two badly-served extremes:**

| Segment | Served by | Gap |
|---|---|---|
| Ultra/HNW | Henley & Partners, Nomad Capitalist — white-glove human advisory, high fees | priced out / overkill for the mass-affluent |
| DIY filers | MyExpatTaxes, TaxesForExpats, Greenback, TurboTax | *compliance/filing only* — no forward *optimisation* or relocation strategy |
| **Mass-affluent mobile earners (the target)** | **almost nobody, AI-native** | **"where should I be tax-resident, what's the legal outcome, and how do I qualify?" — unanswered at their price point** |

B2B AI-tax tools (TaxGPT, Instead "finds every deduction", Orbitax, Altruist/Hazel) are real but aimed at **CPAs/firms** and largely **US-domestic**. An **AI-native, cross-border, consumer/prosumer tax-optimisation + relocation-planning agent** is the open lane.

---

## 4. The product

**An AI agent that answers "how do I legally pay the least tax, and where should I live to do it — and how do I qualify?"** for mobile earners — then routes the execution to licensed professionals.

- **Deterministic residency/tax engine** (the moat): given the user's income mix, assets, citizenship, family and mobility, compute — *deterministically* — their current tax position and a ranked set of **legal** alternatives (stay-and-optimise vs relocate), modelling real regimes: **UAE** (0%, 90–183-day TRC), **Switzerland** lump-sum (CHF ~434,700 min base, 21/26 cantons), **Greece** non-dom (€100k flat), **Italy** (€100k flat / 7% pensions), **Cyprus** (60-day rule, non-dom), **Portugal IFICI** (NHR 2.0, 20% flat — old NHR closed 2024), Malta residency (CBI scrapped 2025). Rules change yearly → a *maintained* engine beats static advice.
- **LLM narration** explains the trade-offs in plain language; **never invents numbers** (Imara's faithfulness pattern).
- **Licensed-professional sign-off + execution marketplace:** the AI produces the plan; vetted local tax advisers + immigration agents review, sign off, and execute (this is also the monetisation and the licensing solution).
- **Compliance built in:** GAAR "commercial-substance" checks, CRS/CFC/exit-tax flags, DAC6/MDR disclosure handling, and an audit trail (Imara's hash-chained log).

---

## 5. Legal & regulatory framework — the non-negotiables (this is the moat)

This is where "loophole" startups die and a compliant one wins.

- **Avoidance (legal) vs evasion (illegal).** Stay firmly on legal planning. SA **GAAR** (ss 80A–80L) + **promoter penalties (R100k/month, ×2 >R5M, ×3 >R10M)**; SARS won a R46M GAAR case Oct 2025. Pure-tax-motivated, no-substance structures are exactly what gets struck down.
- **Cross-border disclosure (EU/UK):** **DAC6 / MDR / DOTAS** — *anyone who designs, markets or implements* a reportable cross-border tax arrangement is an **"intermediary" (promoter or service provider)** with **mandatory disclosure** duties; penalties up to **£1M** + daily charges + reputational. An AI that designs/markets cross-border arrangements is squarely an intermediary → must report. **CRS 2.0 + CARF** (crypto) took effect 1 Jan 2026 — *more* transparency, so the product must be a "plan legally" tool, never a "hide money" tool.
- **Who may give tax advice / unauthorised practice:** in the US only **CPAs, EAs, attorneys** have unlimited rights; preparers need a **PTIN**; some states license preparers; operating without credentials = penalties. Solution: position as **software + information**, with **licensed professionals** doing the advice/sign-off (the marketplace).
- **Professional indemnity (PI) insurance** is *required* of tax agents/advisers by regulators — budget for it.
- **CFC / exit taxes:** CFC rules (e.g. US OBBBA 2026, NCTI 12.6%) catch offshore companies; exit/expatriation taxes catch people leaving — both must be modelled, or "relocation" advice backfires.
- **Name/brand:** "Tax me if you can" is catchy but (a) trademark-clear it, and (b) the "loophole/evasion" connotation is a reputational + regulatory liability — lead with *legal tax efficiency + relocation*.

---

## 6. Why Imara's DNA transfers (the unfair advantage)

This is the reason to build it *here*: the hard part of a credible tax product is exactly what Imara already does.

| Imara capability | Direct reuse in "Tax Me If You Can" |
|---|---|
| Deterministic ratio/figure engine (numbers by arithmetic) | the deterministic **tax/residency rule engine** |
| Faithfulness cross-check (claims vs computed facts) | stop the LLM inventing tax numbers |
| Hash-chained audit log | the **audit trail** regulators/PI insurers want |
| Cross-agent corroboration + judge evals | multi-source verification of tax positions |
| Input guard (PII redaction) + (now) operator auth | handling sensitive financial/identity data |
| SA-Tax/SA-Legal agents (POPIA, SARS, Companies Act) | a working template for codifying tax law into agents |
| Deterministic-first + human-in-the-loop ethos | the exact production pattern tax AI requires |

---

## 7. Business model

- **B2C/prosumer subscription** (the "where should I be tax-resident + optimise" analysis) — the underserved mass-affluent tier, priced well below Henley.
- **Advisory + execution marketplace** (take-rate / referral) connecting users to **licensed** local tax advisers and immigration agents — solves licensing AND monetises the high-value execution.
- **B2B white-label** for accounting/relocation firms (same engine, their brand) — mirrors Imara's product-direction pivot seams.
- PI insurance + licensed-partner network are cost lines, not blockers.

---

## 8. Risks & mitigations (summary)

| Risk | Mitigation |
|---|---|
| Avoidance→evasion / GAAR | legal planning only; commercial-substance checks; licensed sign-off; reframe the brand |
| DAC6/MDR intermediary disclosure | build disclosure handling in; legal counsel on reportable-arrangement triggers |
| Unauthorised practice / licensing | software + licensed-professional marketplace, not unlicensed advice |
| AI hallucination in tax | deterministic engine + faithfulness + human sign-off (Imara DNA) |
| CRS/CFC/exit-tax surprises | model them explicitly; transparency-first positioning |
| Jurisdiction law changes (yearly) | maintained, dated rule corpus (Imara's `sa_knowledge` pattern, generalised) |
| Trademark/reputation | clear the name; lead with "legal tax efficiency + relocation" |

---

## 9. Phased build (proposed)

1. **P0 — Scope + legal foundation:** pick the launch corridor (e.g. SA/UK/EU earners → UAE / Greece / Cyprus / Portugal-IFICI), engage a tax lawyer on licensing + DAC6/MDR, line up licensed-partner advisers + PI insurance. (Ruan/lawyer-led.)
2. **P1 — Deterministic residency/tax engine + dated rule corpus** for the launch corridor (reuse Imara's engine + sa_knowledge pattern), with the GAAR/CRS/CFC/exit-tax flags. Fully testable, no LLM in the numbers.
3. **P2 — AI narration + intake** (plain-English "here's your position and your legal options") on top of the engine.
4. **P3 — Licensed-advisor marketplace + sign-off + audit trail.**
5. **P4 — Expand corridors; B2B white-label.**

---

## Sources
- Market: [Precedence — tax tech $60.66B by 2034](https://www.precedenceresearch.com/tax-tech-market) · [Allied — tax advisory $97.1B by 2031](https://www.alliedmarketresearch.com/tax-advisory-services-market-A31503) · [Henley Private Wealth Migration 2026](https://www.henleyglobal.com/newsroom/press-releases/henley-private-wealth-migration-report-2026)
- Competition: [Instead — AI tax agent](https://www.instead.com/) · [Thomson Reuters — AI tax research](https://tax.thomsonreuters.com/blog/how-to-choose-the-best-ai-tax-research-tool/) · [Nomad Capitalist](https://nomadcapitalist.com/)
- AI reliability: [TaxJar — AI agents vs tax engines](https://www.taxjar.com/blog/difference-between-ai-agents-and-tax-engines) · [AWS — deterministic models in regulated industries](https://aws.amazon.com/blogs/machine-learning/overcoming-llm-hallucinations-in-regulated-industries-artificial-geniuss-deterministic-models-on-amazon-nova/)
- Legal: [SARS GAAR R46M judgment 2025](https://www.polity.org.za/article/sars-gets-aggressive-on-tax-avoidance-r46-million-judgment-sends-a-warning-2025-10-24) · [EU DAC6 (European Commission)](https://taxation-customs.ec.europa.eu/taxation/tax-transparency-cooperation/administrative-co-operation-and-mutual-assistance/directive-administrative-cooperation-dac/dac6_en) · [IRS — who can give tax advice](https://www.irs.gov/tax-professionals/understanding-tax-return-preparer-credentials-and-qualifications) · [Sovereign — CRS 2.0 + CARF](https://www.sovereigngroup.com/news/explainer-changes-to-the-global-tax-transparency-framework-crs-2-0-and-the-carf/)
- Regimes: [UAE tax residency (KPMG)](https://kpmg.com/ae/en/insights/tax-insights/uae-tax-resident-and-tax-residency-certificate-guide.html) · [Swiss lump-sum (KPMG)](https://kpmg.com/ch/en/insights/taxes/lump-sum-taxation.html) · [Non-dom Greece/Italy/Cyprus/Malta (Astons)](https://www.astons.com/blog/non-dom-eu-tax-programs/) · [Portugal NHR→IFICI](https://getgoldenvisa.com/non-habitual-resident-portugal)


---

## 10. 2026-06-23 — research refresh (current, sourced) + P1 MVP build spec

Tax rules change yearly, so the launch-corridor facts were re-verified (sources below). **Reframe holds: legal efficiency + relocation, NOT evasion; the tool INFORMS and hands off to a licensed advisor — it does not design/market an arrangement (that act is reportable under DAC6/MDR).**

**Origin — South Africa (cessation of residence):**
- Physical-presence-test residents cease residency after **330 continuous days outside SA**; ordinarily-resident is a facts test.
- **s9H "exit charge":** ceasing SA tax residency triggers a **deemed disposal of worldwide assets at market value** (CGT), **excluding SA immovable property** (and a few categories), on the day before cessation.
- Must **formally notify SARS (RAV01)** and obtain the non-residency confirmation; merely leaving ≠ ceasing. Retirement funds have a 3-year lock nuance.

**Destinations (legal regimes):**
- **UAE:** **0% personal income tax**; **9% corporate** above AED 375k (0% below; free-zone qualifying income 0%). Individual residency 183 days (or 90 + ties); TRC now requires real **substance**. Best fit: employment/active income wanting 0% personal; note corporate tax + substance.
- **Portugal IFICI (NHR 2.0):** NHR ended **1 Jan 2025** → IFICI: **20% flat** on eligible PT professional income + **foreign-income exemption (pensions EXCLUDED)**; eligibility is **narrow** (highly-qualified innovation/R&D/science/tech/health roles, degree EQF6+, no PT residence in prior 5 yrs, 10-yr validity). Most relocators do NOT qualify — flag this.
- **Cyprus non-dom:** **60-day rule** (permanent home + ties) or 183 days; **non-dom for 17 years → 0% SDC on dividends/interest/rental** (effective ~5% with the GHS cap); €250k/5yr extensions from 2026. Best fit: passive/dividend-heavy income.

**Legal frame (the moat, always surfaced):** **CRS** auto-exchange (you cannot hide — accounts are reported; CARF for crypto coming) → this is legal *relocation*, not hiding; **GAAR + substance** (sham/round-tripping fails — you must genuinely move); **DAC6/MDR** (designing/marketing a reportable cross-border arrangement = an "intermediary" duty + penalties → the tool gives information, not arrangements); **licensing** (only a licensed CPA/EA/attorney may *advise* → licensed-advisor hand-off + PI insurance).

**P1 MVP — what I'm building now (`services/relocation_tax.py`):** a deterministic, decision-support **relocation & tax-residency first-pass**. Input: origin (default ZA) + the user's income mix + candidate destinations. Output (from a DATED, SOURCED corpus; no LLM in the numbers): the **SA exit position** (s9H flag + cessation steps), a **per-destination factual card** (residency test, headline regime, how each income type is treated, eligibility gotchas), a deterministic **fit hint** per destination for the income mix, and the **non-negotiable guardrails** (exit tax, substance/GAAR, CRS, DAC6/MDR, licensing/PI). Classified exactly like Imara's `decision_support`: **indicative factual landscape, NOT advice; dated corpus; confirm with a licensed cross-border tax advisor.** P0 (engage a tax lawyer on licensing/DAC6, line up licensed partners + PI, demand-validation) remains Ruan/lawyer-led and is a prerequisite before this is a real product — the engine is the buildable, no-advice core.

**Sources (2025/2026):** PKF / SARS / Tax Consulting SA (s9H + 330-day cessation); PwC Tax Summaries / Chambers (UAE 0% personal + 9% corporate + residency); Global Citizen Solutions / IBA / immigrantinvest (Portugal IFICI eligibility + 20% + pension exclusion); Cyprus Tax Life / Mondaq / Harneys (Cyprus 60-day + 17-yr non-dom 0% SDC); EU Commission / Pinsent Masons / PwC (DAC6/MDR + CRS hallmark D).
