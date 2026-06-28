# Imara — Strategic Improvement Research (self-directed cycle, 2026-06-28)

**How this was produced:** I analysed Imara from the inside (a full session in the codebase), generated my own "where can this actually improve" questions, and ran a 5-thread parallel web-research cycle on the ones that turn on external evidence. Every thread returned a heavily-cited report; the per-thread sources are listed at the end of each section. This document is the synthesis.

**The framing that drove the questions:** Imara is **engineering-mature but evidence-poor and distribution-poor.** The Imara Score™ — the headline product — is an expert-weighted (AHP) heuristic that has **never been calibrated against a single real funding/repayment outcome.** So the honest questions were not "what feature next" but "what makes the Score *trusted, sold, lawful, and defensible*."

---

## The convergent thesis (the surprise)

The five threads were researched independently. They **converge on one strategy**:

> **Land 1–2 design-partner lenders running the Imara Score in *shadow mode*, reached through the *accountant channel*, with a *POPIA-s71-clean* explainability posture and *low-friction consented data ingestion*. That single motion simultaneously (a) starts the outcome-data clock that is the only path to a *validated* score, (b) builds the proprietary SA-SME outcome dataset that is the only *durable* moat, and (c) is reachable now, pre-revenue.**

Threads 1, 2 and 5 independently point at the **same design-partner pilot**; threads 3 and 4 are the **enablers** that make it credible and frictionless. Everything Imara could *build* is secondary to this — which is exactly what the roadmap's "evidence + distribution, not features" headline already said, now backed by external evidence.

---

## Thread 1 — Is an uncalibrated bankability score sellable, and what's the bar?

**Finding:** A judgmental/expert-weighted score is *explicitly defensible for SMEs* (thin outcome data is the norm; AHP/multicriteria SME scoring is a published, accepted class) — **but only as triage / origination-support, never yet as a decision engine.** Model-risk guidance (SR 11-7) makes "outcomes analysis vs actuals" a non-optional validation pillar, so a never-outcome-tested score is, by definition, *un-validated* — sellable as *support*, not as a *decision*.

**The numeric bar buyers expect** (practitioner conventions, cross-confirmed):
- Discrimination: **Gini > 0.40 / AUC > 0.70 / KS > 0.25** = "good"; an SME score at Gini 0.40–0.50 is competitive.
- Stability: **PSI < 0.10**; Calibration: Hosmer–Lemeshow **p > 0.05**.
- Statistical-development floor: **~1,500–2,000 "goods" + ~2,000 "bads"** over a **12-month** performance window (Siddiqi rule of thumb).

**Minimum viable evidence to sell a *pilot* now (needs zero outcomes):** (i) a **conceptual-soundness dossier** (factor theory, AHP weight derivation, deterministic-first computation, narration-verification — written so an independent reviewer can challenge it); (ii) **benchmark convergence** vs **Altman Z''** (EM-score: >2.60 safe, 2.10–2.60 grey, <2.10 distress) and/or a bureau score on a real sample; (iii) **expert-panel agreement**; (iv) a **stated outcome-validation roadmap** naming the targets above.

**Highest-leverage move from zero outcomes:** **run the Score in shadow / champion-challenger mode on a real lender's book** — scores their live applicants alongside their existing decision, changes nothing, captures both. It is the industry-standard safe way to test a new model and the only thing that ever produces a true Gini/KS.

> **Imara implication:** Already-shipped harness (`outcomes` table, `validation.py`, `score_calibration.py`, `IMARA_PILOT_PROTOCOL.md`) is exactly right and waiting on outcomes. The buildable gap is the **conceptual-soundness dossier** + **Z''-convergence report** (Imara already computes an Altman Z'' convergence — package it as sell material). Never imply "validated" until outcomes land.

*Sources: Financial Innovation (multicriteria SME scoring); World Bank Credit Scoring for SMEs; Fed SR 11-7 (ModelOp, CIMCON); EBA IRB validation handbook 2023; ECB Guide to Internal Models 2024; Siddiqi via uCanalytics; GiniMachine & Anolytics (thresholds); Coralogix/Deepchecks (PSI); Hosmer–Lemeshow; SAS reject inference; Altman Z'' (SciELO, 50-yr retrospective); Cloudbankin/DecisionRules (champion-challenger); NBER w29840.*

---

## Thread 2 — Who is the real buyer/channel in SA?

**Finding:** SA has ~3m MSMEs but a **~R509bn SME credit gap** and only **~5% of formal MSMEs have credit** — and it's a *bankability* problem: only ~46% keep financial records, ~24.6% use formal accounting. National reports explicitly call for "funding readiness" help — **documented demand for exactly what Imara does.** But the SME who most needs a score is the one *least* able to find/trust/pay for a self-serve tool.

Channel verdict:
- **(a) SME-direct self-serve:** structurally the hardest — SMB SaaS converts ~3–8%, churns ~30–45%/yr, and SA adds low financial literacy + price sensitivity. A bankability score is an infrequent, high-stakes purchase — the *worst* fit for high-velocity self-serve. Viable only as cheap top-of-funnel.
- **(b) Embedded / white-label into lenders:** **highest ceiling** (credit-decisioning market ~$8bn→$53.7bn) and the right long-term destination — but a ~198-day enterprise sale with a 7-person buying committee. **A pre-revenue startup cannot open here cold.**
- **(c) Accountant / advisor channel:** **the proven, reachable wedge.** ~50,000 SAICA+SAIPA practitioners sit on the SME's financials *and* trust (~89% call their accountant a "trusted advisor"). Ready-made rails exist (Sage Accountants Program, free Xero partner programme, SAIPA Value Connect). **Bridgement is the locally-validated proof**: integrated into Xero/Sage/QuickBooks, 2-minute apply, approval to R10m in 24h, >R2bn deployed, Xero SA App of the Year 2023 & 2025.

> **Imara implication — recommended GTM:** **Accountant channel as the wedge, explicitly sequenced toward embedded lender distribution as the scale play.** It solves Imara's two hardest problems at once (data + trust), is the only channel with an SA precedent for this exact motion, and every score it produces becomes a lender-ready, consented, pre-scored signal — the on-ramp to channel (b). Fastest path: sign 3–5 progressive practices as design partners, build the **Xero/Sage ledger connection first**, monetise via the practice (per-practice subscription / per-report), and in parallel open **one** embedded conversation with a fast-moving lender (Bridgement/Merchant Capital/Lula — not the big-4 banks yet).

*Sources: FinScope MSME SA 2024; SEDA SMME Quarterly 2024-Q1; McKinsey "A credit lifeline"; IFC/SME Finance Forum; Finfind/African Bank 2025; OECD Financing SMEs 2026 (SA); ChartMogul 2026; Optif/Kalungi (churn); Yoco (Disrupt Africa/Wikipedia); Lula/Merchant Capital/Retail Capital/TymeBank; Bridgement/Xero (verified); SAICA/SAIPA; Sage/Xero partner programmes.*

---

## Thread 3 — Regulatory exposure (the "accidental credit bureau" + POPIA question)

**Finding — the scope fact that reshapes everything:** Imara scores **SMEs (juristic persons)**, not consumers. The **NCA** is built around consumers and largely excludes juristic persons (credit agreements excluded where the juristic person's turnover/assets ≥ R1m). So the NCA's **credit-bureau trigger (s43(1))** — which is conjunctive: *receive/investigate* credit data **AND** *compile/maintain a database* **AND** *issue reports on consumers for payment* — **does not bite** as long as Imara stays advisory, works off the client's *own* data, and does **not** build-and-resell a third-party credit-information database. Imara is never a "credit provider" because it doesn't extend credit.

**The real obligation is POPIA — principally s71 (automated decision-making).** A 0–100 creditworthiness profile is squarely "credit worthiness" profiling under s71(1). The escape hatch is **"based solely"**: because Imara is *decision-support* and a **human (the lender) makes the actual decision**, s71(1) is not engaged. Backup defence: the s71(2)(a) contract exception **with** s71(3) safeguards (a route to **make representations** + disclosure of the **"underlying logic"**).

**FSCA–PA Joint AI Report (24 Nov 2025) is the de-facto product spec:** clear disclosure when AI is used in credit-impacting decisions; **SHAP/LIME explainability** (named); regular **bias audits**; model-risk governance + board oversight; POPIA alignment. Even if Imara isn't itself an FSP, its lender clients are and will push these onto it contractually.

> **Imara implication — compliance checklist (do/avoid):** stay strictly advisory/non-binding; analyse the client's *own* data; **never** warehouse-and-resell a cross-client credit database (the one act that forces bureau registration); contractually require **meaningful human decisioning** (defeats s71 "based solely"); ship **per-score reason codes / factor attributions** (satisfies POPIA s71(3) *and* lets a lender meet NCA s62 "dominant reason"); add **contestability** (query/correct/appeal a score); run and **document bias audits**; disclose AI use; appoint an Information Officer + DPIA. Imara already has `reason_codes.py` + `model_card.py` — extend them into a per-score factor-attribution + an "audit pack" (model card + bias report + explainability samples + DPIA).

*Sources: NCA 34/2005 s1/s43(1)/s62/s70 (justice.gov.za); NCA juristic-person thresholds (Property24, Banking Assoc); Lexology/SAIFM fintech-regulation (reseller bureau); POPIA s71 (popia.co.za, De Rebus, PULP 2024); Michalsons (juristic persons; "based solely"); FSCA–PA Joint AI Report Nov 2025 (ENSafrica, Mondaq, Masthead); draft National AI Policy (Fasken, Adams & Adams).*

---

## Thread 4 — Could open banking replace fragile PDF bank-statement uploads?

**Finding:** Programmatic, consented bank-data aggregation is **viable, proven, and growing** in SA — but there is **no open-banking mandate**, access is mostly consent-based **screen-scraping** (ToS/liability grey zone), coverage is uneven, and reliability has a **~10% breakage tail**. Proof point: **Wonga used Stitch to cut funding from hours to <10 minutes**, replacing manual statement uploads and removing the statement-fraud vector. Providers: **truID** (closest fit — purpose-built SA SME statement/affordability aggregator, statements + structured JSON, deepest lender roster, but least-capitalised and scraping-based), **Stitch** (well-capitalised hedge, 8-bank coverage moving to bank-native rails, but its standalone data product is de-emphasised), **Mono** (avoid for SA — dormant beta, now inside Flutterwave). Drop Ozow (payments only) and "Finchatbot" (not an aggregator).

**Fallback parsing reality:** off-the-shelf PDF parsers hit only **81–95%** *field*-level accuracy (not the marketed "99%"), with acute SA pitfalls (DD/MM/YYYY, the "R" symbol, multi-page tables, layout drift). The defining best practice is **forward balance reconciliation** (`opening + credits − debits` must tie out; mismatches flag rows) wrapped around hybrid OCR/CV+LLM with confidence-gated review, plus **PDF-metadata fraud detection** (genuine bank PDFs show producers like "Finacle"; tampered ones show "Adobe Acrobat"/"iLovePDF").

> **Imara implication:** **Integrate aggregation as a *supplement* (truID primary, Stitch hedge), keep PDF parsing as the universal fallback — and harden that parser, because it currently does NEITHER balance reconciliation NOR fraud-metadata detection** (verified in `services/file_parser.py`). Phasing: (1) ship parser hardening first (reconciliation hard-gate + metadata fraud check) — low-risk, improves the path 100% of SMEs use today; (2) pilot truID on one consenting cohort; (3) add Stitch; (4) revisit Nedbank/Capitec bank-native APIs as the COFI Bill firms up.

*Sources: stitch.money Wonga case study (verified); truID/Stitch/Mono docs; SARB 2020 open-banking consultation; FSCA Open Finance recommendations 2024; IFWG 2021; independent PDF-parser benchmarks; balance-reconciliation & PDF-metadata-forensics best-practice literature.*

---

## Thread 5 — Is the anti-hallucination moat eroding?

**Finding:** The "grounded / number-traceable / verified" claim is now **near-universal**, and the field has converged on exactly Imara's pattern (deterministic calc engine; LLM narrates; verify narration). McKinsey/Gartner already frame anti-hallucination as **table-stakes** ("from AI table-stakes to AI advantage"; hallucination is the #1 blocker for 64% of enterprise buyers — i.e., an *entry condition*). Imara's verified-narration is genuinely best-in-class today — in the same conversation as Rogo (34%→3.9% hallucination), Hebbia (cell-level citations), Concourse (exposes the SQL/Python), Fathom (hover-to-source numbers) and Xero JAX Assure — **but most attach traceability only to numbers, not every sentence, and the whole field is converging here.** Stanford measured **17–33% hallucination even on "grounded + cited" legal tools**, and Big-4 tools (Deloitte Zora, KPMG Clara) were publicly embarrassed by fabricated citations — the giants are weakest exactly where Imara is strong.

**Verdict:** anti-hallucination is a **strong wedge to win deals in 2026, not a moat to defend in 2028.** The next defensible layer (VC consensus — a16z Process Power + proprietary data; Bessemer "memory/context"; fintech-vertical "regulatory-grade audit trail") is **around** the model.

> **Imara implication — evolve the moat (the 3 things to own next):**
> 1. **A SARS/SA-regulatory-grade, examination-survivable audit trail *as a product*** — every number reproducible and **cited to the specific SARS provision**, with version/jurisdiction accuracy and "superseded guidance" flagging. Best fit for Imara's existing deterministic + SARS-cited tax engine; the exact place the Big-4 are failing. *"We can prove how every figure was derived, to SARS"* is a claim no horizontal copilot — and no SA competitor — can match.
> 2. **An outcome-calibrated proprietary SA-SME scoring flywheel** — every engagement feeds an SA-specific outcome dataset (defaulted / funded / survived an audit) that offshore generalists cannot assemble. This is *also* Thread 1's validation path and Thread 2's lender-readiness signal — the same flywheel.
> 3. **Workflow lock-in as the system of record** for the SME's financial truth (numbers + narration + audit trail + SARS filing reconcile in one place).

*Sources: Rogo (OpenAI case study, Lex); Hebbia; Concourse; Digits (Accounting Today); Fathom; Xero JAX Assure; Stanford legal-RAG hallucination study; "Proof-Carrying Numbers" arXiv 2509.06902; McKinsey "AI table-stakes to advantage"; a16z "AI will eat application software"; Bessemer State of AI 2025; fintech.global vertical-AI compliance.*

---

## Prioritised recommendations

**Tier 0 — the real unlock (Ruan-led; I cannot do it):**
- **Sign 1–2 design-partner relationships and run the Score in shadow mode** — reached via the **accountant channel** (3–5 progressive Xero/Sage-certified practices) and **one** fast-moving lender (Bridgement / Merchant Capital / Lula). This is the single highest-leverage action and the convergent answer of Threads 1, 2 and 5. The pilot harness is already built.

**Tier 1 — I can build now, directly enabling the pilot (low-risk, high-leverage):**
1. **Conceptual-soundness dossier + Z''-convergence report** — package the AHP weight derivation, deterministic-first computation, narration-verification, and the already-computed Altman Z'' convergence as the *sell material* that gets a shadow-mode pilot signed (Thread 1). Mostly assembly of what exists.
2. **Per-score reason codes / factor attribution + contestability** — extend `reason_codes.py`/`model_card.py` into a per-score "why this score" breakdown + an appeal route. Satisfies **POPIA s71(3)**, lets a lender meet **NCA s62**, and matches the **FSCA SHAP/LIME** expectation (Thread 3). Also a trust/UX win.
3. **Bank-statement parser hardening** — add **forward balance reconciliation** (hard gate) + **PDF-metadata fraud detection** to `file_parser.py` (currently has neither; Thread 4). Improves the path 100% of SMEs use today and kills a fraud vector.
4. **"Audit-survivable, SARS-cited" packaging of the tax engine** — surface the provision citations the deterministic tax engines already carry as a per-figure audit trail (Thread 5, moat layer #1). Builds on this session's tax work.

**Tier 2 — sequenced after a pilot exists:**
- Bank-data aggregation integration (truID primary, Stitch hedge) — Thread 4.
- Embedded/white-label lender distribution — Thread 2's scale play.
- Outcome-calibrated Score recalibration — Thread 1, once ≥30–50 labelled outcomes land.

**Explicit non-recommendation:** do **not** add more analytical surface area (agents/panels/features) until the pilot exists. All five threads independently say the bottleneck is evidence + distribution, not features.

---

## Caveats on the evidence
- Gini/AUC/KS/PSI bands and the 1,500–2,000 sample figures are **practitioner conventions**, not legislated standards — the numbers buyers expect, not law.
- Several SA-specific data points are thin or vendor-reported: SA SME SaaS CAC/churn (undisclosed), "% of SMEs using an accountant" (no verified SA figure), truID/Stitch 2026 per-bank coverage + pricing (quote-only), and most vendor accuracy claims (self-reported, only Stanford independently measured). Validate commercials and coverage in writing before betting on them.
- POPIA s71 currently has a known *notification* gap and FSCA AI guidance is supervisory expectation, not yet binding law — treat the checklist as forward-defensible posture, not minimum compliance.
