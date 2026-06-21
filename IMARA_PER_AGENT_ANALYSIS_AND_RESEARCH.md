# Imara — Per-Agent Analysis, Research Cycle & Improvement Map

**Date:** 21 June 2026
**Scope:** Every agent in the Imara pipeline, analysed individually, each grounded against a fresh research cycle, with concrete improvement opportunities.

---

## How to read this

For each agent: **Role** (what it is) → **Current approach** (anchored to the actual prompt/code) → **Research & best practice** (what the field says today) → **Improvements** (specific, buildable).

Three things matter more than any single agent finding, so they are called out first as **cross-cutting themes**, then the prioritised backlog sits at the end.

### Cross-cutting themes (true for many agents at once)

1. **Benchmark provenance & SA-localisation.** Most specialist agents carry hard-coded benchmarks (email open 21.5%, win rate 20–30%, OEE 85%, fuel 22% of revenue). Almost all are US/global. SA SME data is thin but real research shows SA small firms behave differently (higher turnover-per-worker than large firms, different cost structures). Benchmarks should carry a *provenance label* and be SA-localised where data exists.

2. **Recency of hard-coded regulatory/market numbers.** Three live numbers are already stale or about to be: the VAT registration threshold (now **R2.3M**, up from R1M, effective 1 April 2026), SARS/repo-linked interest (prompt hard-codes **10.25%**, implying the old 6.75% repo; repo is now **7%**, prime **10.5%**), and the prime-rate anchor the Credit agent relies on. These should be injected from a single dated config, not frozen in prompts.

3. **Claim-level numeric grounding.** The field's 2025 answer to LLM numeric hallucination is claim verification ("proof-carrying numbers"): every figure an agent cites should trace back to an input figure or an explicit arithmetic step. Imara's deterministic-first DNA already does this for scores; extending a lightweight version to *every finding's* `financial_impact` is the highest-leverage reliability upgrade.

---

# Cluster A — Orchestration & Scoring

## 1. CEOAgent (orchestrator: business model → synthesis → scoring → report)

**Role.** Runs the whole chain in five phases: extracts the business model (profile beats extraction), injects `primary_concern` into Phases 1/3/5, writes the SCR synthesis narrative, computes the penalty-weighted score deterministically, and assembles the report.

**Current approach.** Sequential single chain. Phase 4 scoring is deterministic (no Claude call) — good. Profile-wins rule enforced in `_build_business_model()`.

**Research & best practice.** Multi-agent finance architectures (ERSJ 2025) converge on a *Strategist / Critic / Moderator* triad — i.e. an explicit **critic** pass that challenges the synthesis before it's finalised. Imara has the synthesiser and the scorer but no adversarial critic.

**Improvements.**
- Add an optional **Critic pass** between Phase 3 (synthesis) and Phase 5 (report): one cheap call whose only job is "where does this narrative over-claim relative to the findings?" Feeds a confidence caveat, doesn't change the score.
- The CEO already de-dupes; consider surfacing **finding-conflict** explicitly (e.g. Financial says margin is fine, Accounting says COGS is misclassified — these interact). A short "where agents disagree" block is high signal for a credit committee.

---

# Cluster B — Financial Forensics Core

## 2. FinancialAgent (Financial Forensics Partner)

**Role.** Finds margin, cost, working-capital, concentration and EBITDA-bridge leakage; ranks by rand impact.

**Current approach.** Strong, quantified prompt. Relies on the model to compute the rand impact of each gap.

**Research & best practice.** FAITH (2508.05201) and Proof-Carrying Numbers (2509.06902) show that even with correct inputs, LLMs cite the right dataset but the wrong figure. The fix is arithmetic offloaded to code + claim verification.

**Improvements.**
- Move the **EBITDA bridge and working-capital arithmetic into `financial_ratios.py`** (deterministic) and have the agent *narrate* the computed numbers rather than produce them. This is the same pattern that fixed the simulator — apply it here.
- Add a **revenue-concentration computation** from the actual debtor/customer data when present, instead of relying on the model to infer ">20%".

## 3. AccountingAgent (forensic bookkeeper)

**Role.** Duplicates, misclassification, missing accruals, VAT inconsistencies, reconciliation breaks, MoM anomalies, data-quality score.

**Current approach.** Prompt-driven detection over extracted text.

**Research & best practice.** Duplicate-payment and round-number detection are *deterministic* operations — they're exact string/number matching, not judgement. Doing them in the LLM invites both misses and false flags.

**Improvements.**
- Add a deterministic **duplicate-transaction & round-number scanner** in `services/` that runs over parsed line items and hands the agent a candidate list to explain. Cheaper, exhaustive, and verifiable.
- Make the **data-quality score** a computed metric (% rows parsed cleanly, % with missing fields) rather than an LLM estimate — it already has the parse stats from `file_parser.py`.

## 4. AuditorAgent (forensic auditor / internal controls)

**Role.** Benford, vendor concentration, approval-bypass, SoD, revenue timing, related-party, ghost employees, asset existence.

**Current approach.** Prompt lists "Benford's Law violations" with no sample-size guard.

**Research & best practice.** This is the clearest single weakness in the whole pipeline. Benford's Law **requires large, heterogeneous datasets**; on small or range-constrained SME data it produces *false positives from natural variation* (NCBI PMC9307211; Statology; ACFE). Benford "is not a fraud detector — it's a filter." An SME with a few hundred transactions is exactly the regime where Benford misleads.

**Improvements.**
- **Gate Benford on N.** Only run/claim a Benford finding when there are enough transaction-level records (rule of thumb ≥300–500, ideally first-digit counts each ≥5). Below that, the agent must say "insufficient data for Benford" rather than invent a violation. The Fraud agent already hedges with "where available"; the Auditor prompt does not — fix the Auditor prompt.
- When Benford *is* run, label it a **filter that flags accounts for review**, never a conclusion. Pair every Benford flag with a second corroborating signal before it's allowed to be `high`/`critical`.

---

# Cluster C — Risk, Credit, Value, Forecast

## 5. FraudDetectionAgent (Certified Fraud Examiner)

**Role.** Revenue/expense/payroll/cash anomalies, margin manipulation, SoD, Benford, related-party, VAT fraud.

**Current approach.** Good hedging ("where available"). Overlaps materially with AuditorAgent and AccountingAgent.

**Research & best practice.** Same Benford caveat. Also: three agents (Accounting, Auditor, Fraud) independently look for duplicates / round numbers / SoD — risk of triple-counting the same issue at three severities.

**Improvements.**
- Share the **deterministic duplicate/round-number/SoD scanner** (built once) across all three agents so they explain the *same* candidate set from different angles instead of re-detecting and inflating.
- Add a **de-dupe guard at synthesis** so the same underlying transaction can't appear as three separate "critical" findings.

## 6. CreditReadinessAgent (ex-SME lending head)

**Role.** DSCR, leverage, profitability, working capital, collateral, governance, compliance, banking conduct, rate sensitivity, SA funder fit.

**Current approach.** Prices debt at "prime plus 3–5%" and stress-tests "+200bps" — but **the current prime is not injected**; the model supplies it from training memory.

**Research & best practice.** SA prime is **10.5%** as of the SARB's 28 May 2026 +25bps hike (repo 7% + 3.5% spread). A model relying on its cutoff may assume ~11.75% or an old number, mis-pricing every DSCR stress test.

**Improvements.**
- **Inject the current prime rate** (10.5%, dated) from the same config that feeds the macro/Economics agent, so the affordability and +200bps stress are anchored to today, not the model's guess.
- Compute **DSCR deterministically** (operating cash flow ÷ modelled debt service at injected prime) and have the agent interpret it. DSCR is the single most-quoted number a credit committee reads — it must be exact.

## 7. ValuationAgent (CFA / registered valuator)

**Role.** Normalised EBITDA, EBITDA multiple (2.5x–5x SA SME), DCF sanity check, asset floor; low/mid/high ZAR range.

**Current approach.** Range and discounts (concentration, key-person, marketability) are sound and SA-aware.

**Research & best practice.** Confirmed current: SA SMEs trade at a **15–25% discount to UK/European comparables** (emerging-market risk, ZAR volatility, infrastructure); a "small-company discount" applies below ~$2M EBITDA. Imara's 2.5x–5x band already reflects this — it's one of the better-calibrated agents.

**Improvements.**
- Make the **emerging-market discount explicit and adjustable** (a named 15–25% haircut vs an offshore-buyer scenario) rather than baked silently into the multiple — useful when the report audience is a foreign acquirer.
- Tie the **normalised-EBITDA owner-remuneration adjustment** to the HR agent's market-salary view so the two agents reconcile instead of each guessing market pay.

## 8. ForecastAgent (FP&A specialist)

**Role.** 12-month base/bull/bear scenarios from history.

**Current approach.** Strategic 12-month horizon only. **No weekly liquidity view.**

**Research & best practice.** The SME gold standard for *survival* forecasting is the **13-week rolling, direct-method cash-flow forecast** (Intuit, Dryrun, BPR Global, 2026). Weekly updates improve accuracy ~40%. The 12-month and 13-week views are **complements, not substitutes**: 12-month for growth planning, 13-week for "when does cash run out." Imara has the first, not the second.

**Improvements.**
- Add a **13-week direct-method cash-flow projection** (the same time-phased engine sketched as simulator "Build 4"): opening cash, weekly inflows/outflows, the week cash turns negative. This is the number a bank and an owner both actually act on.
- Label the existing scenarios as the **strategic horizon** and the 13-week as the **liquidity horizon** so they aren't confused.

---

# Cluster D — Operations

## 9. OperationsAgent (Lean Six Sigma Black Belt)

**Role.** Bottlenecks, OEE, capacity, idle/rework, quality cost. OEE benchmark 85% world-class / <50% critical.

**Research & best practice.** OEE 85% "world-class" is the canonical Nakajima figure — globally valid, so this agent is on solid ground. The risk is *applicability*: OEE only means something for asset/throughput businesses; for a services SME it's noise.

**Improvements.**
- **Gate OEE/throughput findings on business type.** If the CEO business-model phase classifies the firm as services/professional, suppress manufacturing-only metrics rather than forcing them.

## 10. LogisticsAgent (fleet optimisation)

**Role.** Fleet utilisation, fuel % of revenue (22% median), labour %, debtor days, dead km, downtime.

**Research & best practice.** Fuel-as-%-of-revenue is highly **fuel-price- and route-sensitive** — a fixed 22% median ages quickly in SA given diesel-price swings.

**Improvements.**
- Make the **fuel benchmark a dated, adjustable input** (tie to the diesel price / inflation feed used by the Economics agent) instead of a frozen 22%.
- Same **business-type gate** as Operations — only fire for transport/distribution firms.

## 11. ProcurementAgent (CPO / supply chain)

**Role.** Savings target (8–12%), supplier concentration (>60% top-3 = critical), payment-term working-capital math, inventory holding cost, PPV, maverick spend.

**Current approach.** The payment-terms and inventory-cost calcs are explicit arithmetic in the prompt — good, but model-executed.

**Improvements.**
- Move the **payment-terms free-working-capital and inventory-holding-cost calcs into code** (deterministic), agent narrates. Pure arithmetic shouldn't run in the LLM.
- Reconcile **supplier concentration with the Auditor's vendor-concentration** finding so they don't double-report.

---

# Cluster E — Commercial

## 12. SalesAgent (Revenue Growth)

**Role.** Win rate (20–30% benchmark), deal size, customer concentration, rev/salesperson, discounting, pipeline velocity, LTV:CAC.

**Research & best practice.** Win-rate and LTV:CAC benchmarks are B2B-SaaS-flavoured and assume CRM-grade pipeline data most SA SMEs don't keep. Many findings will be inferred from absent data → speculation risk.

**Improvements.**
- Add a **data-sufficiency gate**: if pipeline/CRM data isn't present, the agent should report "not assessable from supplied data" rather than infer a win rate. (Mirror the Market agent's honesty rule.)
- Reconcile **customer-concentration** with the Financial agent's revenue-concentration finding — currently two agents compute it separately.

## 13. MarketingAgent (CMO / performance marketing)

**Role.** Spend % of revenue, ROAS, CAC payback, LTV:CAC, email open (21.5%), conversion, retention.

**Research & best practice.** These are classic US digital-marketing medians. For an SA SME with little/no digital spend, most won't compute and the agent risks inventing metrics "inferred from data."

**Improvements.**
- **Provenance-label every benchmark** ("US B2B median") and gate on whether the firm actually runs paid/email channels.
- Where the Market Deep Dive agent found a thin online presence, **route that to the Marketing agent as the primary finding** instead of both agents circling visibility independently.

## 14. StrategyAgent (McKinsey-calibre)

**Role.** Porter, BCG, JTBD, Blue Ocean, Ansoff; model vulnerabilities, undermonetised assets, positioning gaps, adjacencies.

**Research & best practice.** Framework-driven strategy is the agent most prone to *generic, ungrounded* output (the frameworks generate plausible prose regardless of data). 2025 guidance on LLM strategy work stresses grounding recommendations in the firm's actual numbers and the market-intel corpus.

**Improvements.**
- Require every strategic recommendation to **cite a specific finding or market-intel fact** (RAG-style grounding) — no recommendation that couldn't name its evidence.
- Feed the **MarketDeepDive competitor list** directly into the Porter "rivalry/threat" analysis so it's about *named* competitors, not abstractions.

---

# Cluster F — People & Legal

## 15. HRAgent (Chief People Officer)

**Role.** Rev/employee, labour % (warn >40%, crit >50%), overtime, absenteeism, turnover, manager ratio, training.

**Research & best practice.** SA-specific data (Small Business Institute; TIPS) shows SA small firms often have **higher turnover-per-worker and pay than large firms** — so a generic global rev/employee benchmark can mis-flag a healthy SA SME. Detailed SA per-sector rev/employee tables are sparse, so any benchmark must be hedged.

**Improvements.**
- **SA-localise the labour-cost and rev/employee thresholds** where StatsSA/sector data exists; elsewhere widen the bands and label them global.
- Tie **market-salary** to the Valuation agent's owner-remuneration normalisation (single source of truth for "market pay").

## 16. LegalRiskAgent (commercial lawyer)

**Role.** Contract exposure, compliance, employment, POPIA/GDPR, IP, insurance, directors' liability.

**Current approach.** Overlaps heavily with the dedicated SALegalAgent (Phase 2d), which is more SA-specific and reads more context.

**Improvements.**
- **Narrow LegalRiskAgent to commercial/contract risk** and explicitly hand SA statutory compliance (Companies Act, POPIA, LRA, BBBEE) to SALegalAgent, to stop the two producing overlapping POPIA/employment findings at different severities.

---

# Cluster G — SA Regulatory (the recency-critical pair)

## 17. SATaxAgent (Chartered Tax Adviser / SARS practitioner)

**Role.** VAT, CIT/IT14, SBC (≤R20M), PAYE/SDL/UIF, provisional (80% rule), tax clearance, SARS debt.

**Current approach — two confirmed stale numbers:**
- Line 837: *"correctly registered for VAT (mandatory above R1M turnover)."* The compulsory VAT threshold rose to **R2.3M effective 1 April 2026** (voluntary R50k → R120k); turnover-tax limit also R2.3M. **R1M is now wrong** and would tell a R1.5M-turnover firm it must register when it need not.
- Line 864: *"Interest accrues at 10.25% p.a. (repo rate + 3.5%)."* That implies a 6.75% repo; repo is now **7%**, so the figure should be **10.5%**.

**Research & best practice.** Budget 2026 confirmed all of the above (SARS; Standard Bank; CDH; Xero). SBC gross-income ceiling of **R20M is still correct** — keep it.

**Improvements (high priority, concrete).**
- **Update the VAT threshold to R2.3M** (and voluntary R120k) and the **interest figure to 10.5%**, ideally by pulling both from a single dated `sa_rates` config rather than hard-coding in the prompt.
- Add a **dated provenance line** ("rates current as of Budget 2026, 1 April 2026") so the next change is a one-line edit and the report can show its as-of date.

## 18. SALegalAgent (attorney — corporate / BBBEE / POPIA)

**Role.** Companies Act 71/2008, BBBEE (EME <R10M, QSE R10M–R50M), POPIA, LRA, CPA, NCA, CIPC, PIS thresholds.

**Current approach — confirmed correct.** EME <R10M / QSE R10M–R50M match the 2026 codes; PIS logic (>350 audited AFS, >100 independent review) is right; NCA >R500k registration threshold is right.

**Improvements (light).**
- Keep an eye on **BBBEE sector-code** differences (some sectors set different EME/QSE thresholds) — add a one-line "generic codes assumed; sector codes may differ" caveat.
- Move the **PIS computation to code** (it's a formula already written in the prompt) so the threshold call is deterministic.

---

# Cluster H — Market & Macro

## 19. MarketResearchAgent (quick scan) & 20. MarketDeepDiveAgent (deep intel)

**Role.** Quick brand/market scan (Phase 1b) feeding `market_context_summary`; deep competitor/news/opportunity intel (Phase 2b). Both have strong "only state what the data supports / say so when sparse" honesty rules.

**Research & best practice.** These are the **best-disciplined agents** in the system — explicit anti-hallucination rules, quantified outputs. The only gap is *source quality*: they depend on whatever the search returns.

**Improvements.**
- Feed the **named competitor list into Strategy and Marketing** (noted above) so the intel is reused, not re-derived.
- Consider a **second search provider as fallback** (the funding research already mapped options) for resilience if SERPER returns thin results.

## 21. EconomicsAgent (SA macro-economist) — *designed, not yet built*

**Role (planned).** Macro → single-firm bottom-up sensitivity (rates/FX/inflation/electricity), WB+SARB free data, IFRS-9 probability-weighted scenarios into the Action Simulator, a "Macro Resilience" overlay.

**Research & best practice.** This is the natural home for the **dated rate config** that the Credit, Logistics and SA Tax agents all need. Build the config first (prime 10.5%, repo 7%, diesel, CPI) and let those agents consume it — that turns a "future agent" into immediate value for three existing agents.

**Improvements.**
- Build the **shared `sa_rates`/macro config now** (small, dated) even before the full agent — it's the dependency that fixes themes #2 above across Credit, Logistics, and SA Tax.

---

# Prioritised improvement backlog

**P0 — correctness/recency (small, high-value, do first)**
1. SATaxAgent: VAT threshold R1M → **R2.3M**, voluntary → **R120k**, interest **10.25% → 10.5%**; source from a dated config.
2. Credit/Logistics/SA-Tax: introduce a single **dated `sa_rates` macro config** (prime 10.5%, repo 7%, diesel, CPI) and inject it — kills the "model guesses the rate" risk.
3. AuditorAgent: **gate Benford on sample size**, label it a filter, require a corroborating signal before high/critical.

**P1 — reliability (medium)**
4. Deterministic **duplicate / round-number / SoD scanner** shared by Accounting, Auditor, Fraud; de-dupe at synthesis.
5. Move pure arithmetic into code for **Financial (EBITDA bridge), Procurement (payment-terms/inventory), Credit (DSCR), SA-Legal (PIS)** — agents narrate, don't compute.
6. **Data-sufficiency / business-type gates** for Sales, Marketing, Operations, Logistics so absent data → "not assessable", not invented metrics.

**P2 — depth (larger)**
7. ForecastAgent: add the **13-week direct-method cash-flow** (liquidity horizon) alongside the 12-month scenarios.
8. CEOAgent: add a **Critic pass** + a "where agents disagree" block.
9. **SA-localise & provenance-label** all hard-coded benchmarks (HR, Marketing, Sales, Logistics).
10. Reduce **agent overlap**: narrow LegalRisk vs SALegal; reconcile customer-concentration (Financial/Sales) and vendor-concentration (Auditor/Procurement).

---

## Sources

- Benford limitations: [NCBI PMC9307211 — Benford in very small samples](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9307211/) · [Statology](https://www.statology.org/unraveling-the-mystery-of-benfords-law-applications-in-fraud-detection/) · [ACFE workbook](https://www.acfe.com/-/media/images/acfe/products/publication/self-study-cpe/workbook/using-benfords-law/using_benfords_law_sample.pdf)
- SA VAT/SBC/turnover thresholds 2026: [SARS — new VAT threshold](https://www.sars.gov.za/faq/what-is-the-new-threshold-for-vat-registration/) · [Standard Bank — Budget 2026 VAT R2.3M](https://www.standardbank.co.za/southafrica/news-and-media/newsroom/budget-2026-delivers-sme-relief-as-vat-threshold-increases-to-r2.3-million) · [CDH](https://www.cliffedekkerhofmeyr.com/en/news/publications/2026/South-Africa/Tax-Exchange-Control/tax-and-exchange-control-alert-19-march-VAT-threshold-increased-Should-SMEs-remain-registered) · [Xero SA tax guide 2026](https://blog.xero.com/small-business-resources/south-african-tax-dates-2026-2027/)
- BBBEE EME/QSE thresholds: [BEE Ratings-SA](https://beeratings.com/emes-qses-and-start-up-enterprises/) · [Tenders-SA 2026 guide](https://www.tenders-sa.org/blog/bbbee-compliance-tenders-2026-guide)
- SA prime/repo June 2026: [Banking Association SA](https://banking.org.za/news/2026-statement-on-the-prime-interest-rate/) · [Trading Economics — SA interest rate](https://tradingeconomics.com/south-africa/interest-rate) · [SARB current market rates](https://www.resbank.co.za/en/home/what-we-do/statistics/key-statistics/current-market-rates)
- SME valuation multiples 2026: [Consortia Advisory](https://consortiaadvisory.com/business-valuation-multiples-by-industry-2026-complete-ebitda-guide/) · [Equidam EBITDA multiples](https://www.equidam.com/ebitda-multiples-trbc-industries/) · [Dealflow exit valuations 2025-26](https://www.dealflowagent.com/blog/business-exit-valuations-2025-26-complete-guide-ebitda-multiples-sale-prices)
- 13-week cash flow: [Intuit](https://www.intuit.com/enterprise/blog/financials/13-week-cash-flow-forecast/) · [Dryrun](https://www.dryrun.com/blog/mastering-financial-stability-a-13-week-rolling-cash-flow-forecast-guide) · [BPR Global](https://bprglobal.co/resources/financial-planning-analysis/13-week-cash-flow-forecasting-guide/)
- LLM numeric hallucination/guardrails: [Proof-Carrying Numbers (arXiv 2509.06902)](https://arxiv.org/pdf/2509.06902) · [FAITH — tabular finance hallucination (arXiv 2508.05201)](https://arxiv.org/pdf/2508.05201) · [ERSJ 2025 — multi-agent finance architecture](https://ersj.eu/journal/4220/download/Prompt+Engineering+in+Finance+An+LLM-Based+Multi-Agent+Architecture+for+Decision+Support.pdf) · [LLM guardrails 2025](https://www.leanware.co/insights/llm-guardrails)
- SA SME productivity: [Small Business Institute baseline](https://www.smallbusinessinstitute.co.za/wp-content/uploads/2019/01/SBIbaselineStudyAlertfinal.pdf) · [TIPS — economics of SMMEs](https://www.tips.org.za/files/506.pdf)
