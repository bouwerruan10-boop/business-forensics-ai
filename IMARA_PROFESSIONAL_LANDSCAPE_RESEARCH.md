# Imara — Professional-Emulation Research & Improvement Map
*Research cycle: which real-world professionals Imara's agents emulate, how those professionals actually help (and fail) SME clients in South Africa, and what that teaches us about improving Imara. Researched June 2026 via five parallel SA-grounded, source-cited research streams. Statutory figures are sourced; market fees flagged [EST] (SA professional pricing is overwhelmingly quote-based).*

---

## 0. The unifying thesis (read this first)

Across all 30+ professionals studied, one finding dominates and should steer the roadmap:

**South Africa's SME problem is an EVIDENCE-AND-PRESENTATION gap, not a viability gap.** The R350bn–R509bn SME funding gap persists "because many businesses are not funding-ready" — over half of SA SMEs keep no usable financial records, banks misapply consumer-grade scoring, and one major bank won't lend below R10m turnover at all (McKinsey). Viable businesses are declined for *how they present*, not *what they are*.

**Imara's defensible role is therefore the always-on, zero-marginal-cost FIRST PASS that:**
1. **Manufactures the funding-ready artefact** the SME cannot produce itself (clean financials, DSCR, cash-flow story, compliance evidence).
2. **Does the expensive consultant pre-work for free** — the diagnosis/benchmark/triage that humans charge R5k–R150k for.
3. **Tells the SME which expensive humans it actually needs** and prepares the evidence before the meter starts running.

**Two structural blind spots** a financials-only tool misses — and that recurred across clusters:
- **Owner-level risk** (personal credit, personal surety, over-indebtedness, continuity/succession, matrimonial regime) — SA SME credit is *blended* (business + director), so the entity alone is the wrong unit.
- **Collateral & security** (insurance ceded to the lender, registered IP as an asset, notarial bonds) — lenders underwrite security, which Imara currently ignores.

**The honest boundary (every cluster):** Imara emulates the *diagnostic* layer — flag, score, evidence, route. It must NOT cross into the regulated, liability-bearing, on-site, or relational acts (sign AFS, give an audit opinion, represent at SARS/CCMA, draft enforceable legal instruments, act as Information Officer/company secretary, issue a B-BBEE certificate, give FAIS advice, hold a broker mandate). Stating this plainly is itself a trust asset and the basis of "warm hand-off" distribution.

---

## 1. Agent → real-world professional map

| Imara agent / feature | Human professional(s) it emulates |
|---|---|
| Financial, Accounting | Accountant (CA(SA)/SAIPA/CIBA), bookkeeper, management accountant / **virtual CFO** |
| Auditor | External auditor / independent reviewer; **internal auditor** (controls/risk) |
| Fraud Detection | Forensic accountant / Certified Fraud Examiner (CFE) |
| Credit Readiness, bank-signals, lender-view, funding-fit | Bank SME credit analyst / business banker; credit bureau; DFI investment officer (SEFA/IDC/NEF); funding consultant |
| Valuation | Business valuator; business broker (free, conflicted valuations); M&A/corporate-finance advisor |
| Forecast, distress (Altman Z''), What-If Simulator | Virtual CFO (cash-flow); business rescue practitioner / turnaround specialist |
| Operations | Lean/Six-Sigma ops consultant; **industrial engineer** (Pr Eng); **energy/backup-power advisor** (new) |
| Logistics | Supply-chain & logistics consultant (inventory, S&OP, freight-fragility) |
| Procurement, Supplier-Savings | Procurement / strategic-sourcing / cost-reduction consultant (CIPS) |
| HR | HR consultant + labour-law/IR specialist + payroll bureau (CCMA, SDL) |
| Strategy, CEO synthesis | Management/strategy consultant; business coach/mentor (SEDFA) |
| Marketing | Marketing consultant / fractional CMO; **growth/CRO specialist** (new) |
| Sales | Sales consultant / revenue-growth advisor |
| Market Research (1b) | Market research analyst (SAMRA); affordability gap is the wedge |
| Market Deep-Dive (2b) | Competitive-intelligence analyst (battlecards, win/loss) |
| SA Tax, Tax Optimization, Tax-Structure-Risk | Tax practitioner (SARS/RCB); GAAR/SARS scrutiny |
| SA Legal, Legal Risk | Commercial attorney; **company secretary / CIPC** (CGISA); B-BBEE verification/consultant; POPIA Information Officer |
| Economics / Macro overlay | Economist / macro analyst (SARB/BER) — the macro→single-firm translation nobody sells |
| (gap — owner risk) | Debt counsellor; financial planner (CFP); insurance broker (cession); notary |
| (gap — IP/intangibles) | Trademark / IP attorney |
| (gap — transformation) | Enterprise & Supplier Development (ESD) facilitator (B-BBEE) |

---

## 2. Cross-cutting improvement opportunities (the actionable core)

Prioritised by leverage × build-readiness × fit with Imara's "numbers-computed-in-code, LLM-narrates" DNA. Many VALIDATE existing direction; several are genuine white space.

### Tier 1 — deterministic, cheap, high-leverage, build-ready
1. **Public Interest Score (PIS) calculator → assurance-tier recommender.** Compute PIS (employees + R1m-turnover + R1m-third-party-liabilities + beneficial-owner count) from data Imara already ingests; tell the SME *audit / independent review / compilation-only / exempt (owner-managed)*. Directly saves R15k–R50k of needless audit spend. **Likely the single highest-leverage addition.**
2. **CIPC compliance as a hard bankability gate.** From `cipc_number` + incorporation date: annual-return-due, **beneficial-ownership register** on file (mandatory since 1 Jul 2024), days-to-deadline, deregistration risk. A deregistered company is un-bankable by definition → fold into the Imara Score, not just a panel. The 2024–25 deregistration wave makes this urgent and high-frequency.
3. **DSCR-first "lender's credit memo."** Output DSCR (target 1.15–1.25×+), affordability verdict, collateral/security position, and a **5 Cs pass/fail grid** in the bank's own language — converting the Credit Readiness score into the artefact a credit committee actually reads.
4. **Funder-fit matcher wired to REAL SA gates.** Encode SEFA/IDC/NEF/bank eligibility (black-ownership %, ≥95%-SA-staff, citizenship, turnover band, sector mandate, development-impact) against Imara's intake; tell the SME exactly which funder it qualifies for and which gate it fails. No human does this cheaply.
5. **Cash-flow runway / "cash-out date" + profit-vs-cash.** The virtual-CFO's headline value ("profitable but out of cash in month 4") and the #2 SA decline driver (cash *timing*, not profitability). Make the existing 13-week cash-flow the centrepiece; add a debtor-days/payment-regularity signal from bank statements.
6. **Owner-level risk dimension (not just the entity).** Personal credit (blended scoring), personal-surety exposure, over-indebtedness (NCA affordability test), continuity/succession (funded buy-sell, key-person cover). Three separate professionals converge here.
7. **Inventory-efficiency / working-capital-release metric.** Turns, days-inventory-outstanding, cash-trapped-in-stock from financials — pure Imara lane, currently absent, high ROI.
8. **Compliance calendar + FREE on-ramps surfaced.** Next VAT201/IRP6/IT14/EMP201/CIPC dates from tax-year-end + entity data; and surface the cheap/free fixes most SMEs don't know exist — **EME B-BBEE affidavit (free), POPIA Information-Officer registration (free), Workplace Challenge ~90% Lean subsidy, 30-April WSP/ATR + recoverable SDL grant**.
9. **Insurance + cession fundability check.** Lenders (incl. SEFA) *require* cover and take it as security by cession; uninsured/unceded = measurably less fundable. New field + finding.

### Tier 2 — differentiated, higher effort
10. **Proactive fraud-risk screen** (CFE red-flag analytics: Benford's Law, duplicate/round/after-hours payments, supplier-bank-detail changes, ghost employees). SMEs lose ~5% of revenue to fraud (every R1 costs R3.64) yet never engage a forensic accountant (reactive, R30k–R150k). Clearest white space. **Guardrail: indicate risk, never allege fraud.**
11. **ESD / Supplier-Readiness Score** (compliance-ready: CIPC-Active + SARS-TCS-Compliant + CSD-active + B-BBEE affidavit + ≥51% ownership; AND graduation-ready: financials/governance/capacity). Maps exactly onto Imara's document buckets; the B-BBEE Commission's own research says compliance-without-graduation is the system's core failure. Flag the **Jan-2026 draft Transformation Fund** (don't hard-code 1%/2%).
12. **Macro→single-firm translation overlay** (the planned Economics agent): ingest free SARB repo (7.0%, May 2026) + BER + load-shedding data → per-firm rate/FX/inflation/electricity sensitivity. A product that essentially doesn't exist commercially → biggest defensible differentiator. Sourced sensitivity, **not** a fabricated forecast, **not** a Score change.
13. **Energy-resilience overlay + diesel-vs-solar payback** in the What-If Simulator. Load-shedding was the dominant operational risk across *every* ops profile; ROI/payback is computable from a few intake fields.
14. **Productise competitive intelligence** in Market Deep-Dive: real **sales battlecards + competitor profiles + win/loss** with explicit confidence levels (also serves anti-hallucination DNA). Bespoke CI is $8k–30k/project and AI is the named disruptor.
15. **B-BBEE-aware procurement guardrail.** Never recommend a cost-cut that breaks preferential-procurement scoring / drops a B-BBEE level — a documented failure of human cost-reduction consultants that Imara can systematically avoid (tool *safer* than human).
16. **CCMA-exposure estimator + Rule-25 representation explainer** (HR): procedural-compliance checklist (where SMEs actually lose), exposure quantified with sourced statutory caps (12-month compensation, 1-week/yr severance, R7,000 cost cap), SDL >R500k flag.
17. **Growth / CRO unit-economics finding** (CAC, CPA, conversion, revenue/visitor) — the cheapest growth lever, the most Imara-native marketing metric, currently uncovered.
18. **Contract / shareholder-agreement / IP gap checklist** (attorney/IP): missing shareholder agreement, MOI gaps, IP assigned to founder-not-company, unregistered core trademark — high-signal, cheap, fundability-relevant.

### Tier 3 — strategic / product-model
19. **Coach-style accountability loop** — a re-analysis cadence tracking progress vs prior recommendations. Clients renew for recurring accountability, not one-shot decks (the #1 consultant failure mode); seeds recurring revenue for any mass-distribution pivot.
20. **Map every recommendation to a named SA capital source** — make fundability the explicit spine (the most-paid-for consultant deliverable).
21. **Cheap primary-data hook** (mobile-first WhatsApp survey, e.g. Yazi-style) — closes Imara's one structural research blind spot (it never asks real customers) at an SME-affordable price; 65%+ of SMEs fail on market fit yet <25% buy research.
22. **Exit / sale-readiness mode** — Imara's independent, methodology-transparent valuation already beats the broker's conflicted close-biased number; add "what a buyer's due diligence would flag."

### Cross-cutting positioning
- **Position at the SME-appropriate tier** — emulate the Professional Accountant (SA) / **virtual-CFO co-pilot**, not a pretend CA(SA)/auditor.
- **Add a "books / data-confidence" indicator** (the bookkeeper's reconciliation discipline) so users know when records are too messy to trust the report — and flag "this needs a bookkeeper."
- **Adopt an explicit honest-broker / anti-scam stance** (the DFI-consultant market is full of "guaranteed funding" upfront-fee scams) — differentiate as the honest readiness layer.
- **Adopt the internal auditor's finding discipline** (Condition/Criteria/Impact + Management Action Plan w/ owner+timeline + follow-up) — Imara's AgentFinding + Roadmap are already 90% of this; lean in and broaden to control-design gaps (segregation of duties, approval controls).

---

## 3. Per-cluster highlights (distilled)

### Cluster A — Accounting, audit, tax, fraud
- **The SA tier matters:** only *audit* is statutorily reserved (IRBA). A Professional Accountant (SA)/CIBA can legally compile + sign AFS — most SMEs are over-served/over-charged by reaching for a CA(SA). Position Imara at the SME tier.
- **Virtual CFO is Imara's closest analogue** (R15k–R60k/mo vs full-time CFO R0.8–1.5m/yr). Headline value = cash-flow forecasting + profit-vs-cash.
- **PIS / assurance-tier** and **CIPC + beneficial-ownership** are the two sharpest deterministic wins.
- **Forensic/fraud** is the clearest white space (proactive screen vs reactive R30k–R150k human).
- Fees (sourced): AFS compile R3.5k–R25k+; IT14 R2.5k–R6.5k+; VAT201 R1.5k–R5k; small-business audit R15k–R50k; forensic R2.5k–R5k/hr.

### Cluster B — Funding, credit, valuation, distress
- **Core decline drivers (in order):** no usable records; cash-flow *timing* (SA pays in 30–150+ days; R12.4bn govt arrears); collateral gap; **blended** business+director credit (Experian Commercial Delphi, TransUnion, XDS, Compuscan); consumer-grade scoring misfit; the **5 Cs + DSCR ≥1.15–1.25×**.
- **The fix the market is converging on = alternative data** (transaction-flow regularity) → Imara can read this from bank statements.
- **Distress/Altman → reframe as early-warning + runway** ("financially distressed" = can't pay debts in 6 months); business-rescue success only ~36%, so timing is everything.
- **Anti-scam honest-broker posture** is both ethical and a trust wedge.

### Cluster C — Operations, supply chain, HR, procurement
- Splits into work Imara can *do* (inventory, spend, compliance, payback, readiness — number/document/rule-driven) vs work it can only *prepare for and route to* (time-and-motion, the floor, the hearing, the install). Be explicit.
- **ESD / supplier-readiness** = most differentiated SA opportunity (maps to existing buckets).
- **Energy/backup-power advisor** = the added professional; load-shedding is the dominant ops risk and has no owning agent; payback is computable.
- **B-BBEE-aware procurement guardrail** = tool safer than human.
- Sourced SA hooks: Workplace Challenge ~90% Lean subsidy; CCMA cost cap R7,000; SDL on payroll >R500k; B-BBEE ESD ~40/107 points with 40% sub-minima (one miss drops a level).

### Cluster D — Strategy, marketing, sales, market intelligence
- **Most exposed to the creativity/judgement gap** — be honest: replace the *commodity* work (scans, diagnostics, structured plans, benchmarks), not bespoke strategy/creative/coaching.
- **Productise CI** (battlecards/profiles/win-loss) — bespoke CI $8k–30k, AI is the disruptor → clearest market gap.
- **Growth/CRO** = added professional; unit economics are Imara-native and uncovered.
- **Accountability loop** (coach) drives retention; **fundability spine** (route to named capital) is the truest mission expression.
- **Market-research affordability gap:** 65%+ SMEs fail on market fit, <25% buy research → Imara's instant scan IS the disruptive substitute; close the primary-data gap cheaply (WhatsApp surveys).

### Cluster E — Legal, governance, compliance, macro, brokerage + "unrelated"
- **CIPC deregistration regime** = sharpest, cheapest, most existential win (also in Cluster A).
- **Macro→single-firm translation** = biggest unserved gap and defensible differentiator (the Economics agent).
- **The "unrelated" professionals were the richest surprise** — all bear on bankability via **(i) collateral/security** or **(ii) owner-level risk**:
  - **Insurance broker — the standout:** lenders *require* cover and take it as security by **cession** (SEFA names it). Uninsured/unceded = less fundable.
  - **Debt counsellor — the distressed/fundable boundary:** the NCA reckless-lending/affordability test is the exact lens lenders apply; owner under debt review = can't take new credit.
  - **Financial planner — continuity risk:** owner-business entanglement (death/disability/exit) is a top credit question; funded buy-sell + key-person cover answer it.
  - **Trademark/IP attorney:** registered mark = balance-sheet intangible + moat; unprotected brand = risk to the business securing the loan.
  - **Notary:** notarial bond (security over movables) + matrimonial regime (who can bind the business / whose estate backs a surety).
- Free on-ramps to surface: **EME B-BBEE affidavit (free), POPIA IO registration (free)**.

---

## 4. What Imara must NOT replace (the hand-off list)
Sign/compile AFS · give an audit/assurance opinion · represent before SARS or chair/represent at the CCMA · draft enforceable legal instruments or give legal advice · act as appointed Company Secretary or Information Officer · issue a B-BBEE verification certificate or sworn affidavit · give FAIS financial/insurance advice or sell product · act as a statutory Business Rescue Practitioner · hold a broker's Fidelity Fund Certificate / sale mandate · run time-and-motion / site fieldwork / installations · deliver bespoke creative, the human coaching relationship, or live negotiation. For each: **decision-support + warm hand-off to the credentialed human** — the always-on first pass that prepares the evidence before the meter runs.

---

*Method: five parallel general-purpose research agents, SA-grounded, source-cited (McKinsey SA SME lending; SARB/BER; SEFA/IDC/NEF; IRBA/SARS/CIPC/SANAS/Information Regulator/NCR/CCMA/ECSA; professional bodies SAICA/SAIPA/CIBA/SAIT/ACFE-SA/SAPICS/CILTSA/CIPS/SABPP/MASA/SAMRA/SCIP/COMENSA/CGISA/LPC/FPI; B-BBEE Commission; dtic). Full per-professional source URLs retained in the research stream outputs. Market fees flagged [EST]; statutory figures sourced.*
