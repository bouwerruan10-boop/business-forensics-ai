# Imara — SARS / SA Tax Deep Research (gap analysis + build spec)
_Researched 2026-06-27 for the "Tax Me If You Can" engine. Scope: domestic SARS engine + cross-border, owner + entity, all four emphases (calculations · TAA process · audit-risk · taxpayer rights)._

> **Method note.** The deep-research workflow engine failed repeatedly (StructuredOutput cap), so this was compiled from **direct SARS / Act / SA-tax-firm source searches**. Figures are cited but **must be confirmed against the live SARS source + dated in `sa_rates.py` before any calc ships** (deterministic-first discipline). Budget 2026 moved several figures (effective 25 Feb / 1 Apr 2026) — flagged inline.

---

## 1. Gap analysis — engine coverage vs the SARS universe

Legend: ✅ in engine · ◑ partial · 🔲 missing

### Layer 1 — Tax-type CALCULATIONS
| Item | Key rule / figure (cited) | Engine |
|---|---|---|
| Individual income tax | 2026/27 brackets + rebates R17,820/9,765/3,249 | ✅ `income_tax.py` |
| VAT | 15/115, VAT201 categories | ✅ `vat_calc.py` |
| ETI | 1-Apr-2025 bands (60%/30%, R1,500/R750, taper) | ✅ `eti.py` |
| Provisional (IRP6) | payments + par-20 penalty (20%) | ✅ `provisional_tax.py` |
| SBC / company tax | s12E graduated + 27% flat | ✅ `sa_rates.py` |
| Travel allowance | s8(1)(b) 80/20 + R4.95/km flat | ◑ flat only — **deemed-cost fixed-cost table by vehicle value missing**; subsistence R595/R184 missing |
| **CGT (8th Sch)** | individual incl. **40%**, company/trust **80%**; annual exclusion **R50,000** (↑ from R40k, 25 Feb 2026); primary-residence exclusion **R3m** (↑ from R2m); max effective individual ≈18% | 🔲 (only `SA_CGT_EFFECTIVE=0.18` constant) |
| **Fringe benefits (7th Sch)** | company car **3.5%/mo** of determined value (**3.25%** with maintenance plan); low-interest loan at **official rate = repo+1% = 7.75%** (1 Dec 2025); residential accommodation = lower of formula/cost | 🔲 |
| **Lump sums** | retirement-fund + severance tables, **R550,000 tax-free**, ring-fenced, **cumulative lifetime** aggregation | 🔲 |
| **Assessed losses** | s20 company ring-fencing (**R1m or 80%** of taxable income cap); s20A individual suspect-trade ring-fencing | 🔲 (only flagged as risk) |
| **Turnover tax (6th Sch)** | threshold **R2.3m** (↑ from R1m, 1 Apr 2026); graduated rate table | ◑ threshold constant only |
| **Interest on tax** | prescribed rate ≈**10.5%** p.a. | ◑ `SARS_INTEREST_RATE` exists, not applied |
| **Admin penalty (s210/211)** | fixed-amount table by taxable income, **R250–R16,000/month**, recurs up to **35 months** | 🔲 |
| **Understatement penalty (s222/223)** | behaviour table: substantial understatement **10%** (20% obstruction/repeat), reasonable-care-not-taken, no-reasonable-grounds, gross negligence **100%**, intentional evasion up to **200%**; 2026 amendment narrowed the "bona fide inadvertent error" defence | 🔲 (qualitative flags only) |
| Dividends/withholding | dividends 20%, interest WHT 15%, royalties 15% | ◑ dividends in `relocation_tax` |
| Capital allowances | s11(e), s12C (40/20/20/20), s12E, s13 | 🔲 |
| Donations | s18A (10% cap) + donations tax 20%/25% | ◑ s18A in `relocation_tax` |

### Layer 2 — SARS / TAA PROCESS MACHINERY
| Item | Key rule (cited) | Engine |
|---|---|---|
| Compliance calendar | VAT201/IT14/IRP6/EMP201/EMP501 | ✅ `compliance_calendar.py` |
| **Auto-assessment** | 2026 season: auto-assessments **1–12 July**, season opens 13 July; **40 business days** to accept/edit; non-provisional eFiling deadline **23 Oct 2026**; refunds in **72h**; provisional taxpayers can opt out | 🔲 |
| **Assessments** | original, additional (s92), reduced (s93), estimated/jeopardy (s95); 3-year prescription | 🔲 |
| **Verification vs audit** | **21-business-day** relevant-material request; verification ≠ audit | 🔲 |
| **Disputes** | request for reasons (**45 bus. days**, pauses the clock) → objection **NOO within 80 bus. days** → appeal **NOA within 30 bus. days** → ADR → Tax Board → Tax Court; extensions 30 days / up to 3 years | 🔲 |
| **Tax Compliance Status** | My Compliance Profile, **4 pillars**: registration · submission · debt · relevant material; TCS PIN; "good standing" | ◑ `tax_clearance_status` field only |
| **Debt** | "pay now, argue later"; **s164** suspension of payment pending dispute; **s167** instalment arrangements; **s200/201** compromise; **s179** third-party/bank appointment; write-off s197-8 | 🔲 |
| **VDP** | s225–233 voluntary disclosure — relief from understatement penalty | 🔲 |
| **Record-keeping** | s29–32 — **5 years** | 🔲 |

### Layer 3 — AUDIT-RISK INTELLIGENCE
| Item | Key rule (cited) | Engine |
|---|---|---|
| Risk flags | related-party, low ETR, VAT gap, cash-vs-turnover | ✅ `tax_risk_flags.py` |
| **Audit triggers** | third-party **IT3 data mismatch** (banks/employers/medical/retirement feed SARS), VAT refunds, repeated losses, lifestyle audits, large/unusual deductions | ◑ partial |
| **GAAR (s80A–L)** | arrangement + tax benefit + **sole/main purpose** + tainted element (abnormality / lack of commercial substance / misuse); **presumption is reversed onto the taxpayer**; *ABSA* ConCourt 2026 broadened "party" reach | ◑ qualitative |
| **USP exposure** | map a flag → likely behaviour band (10/100/200%) | 🔲 |
| **Reportable arrangements** | s34–39 — disclosure duty + penalties | 🔲 |

### Layer 4 — CROSS-BORDER (the flagship)
| Item | Key rule (cited) | Engine |
|---|---|---|
| Relocation first-pass | indicative destination/regime cards | ✅ `relocation_tax.py` |
| **Residency tests** | ordinarily resident (common law) + **physical presence** (>91 days current yr **and** each of 5 prior yrs **and** >915 aggregate over 5 yrs); cease if **330 continuous days** outside | ◑ days_abroad input only |
| **Exit tax s9H** | deemed disposal of worldwide assets (excl. SA immovable) the **day before** ceasing; inform SARS within **21 days**; update **RAV01**; CGT ≈18% max | ◑ mentioned |
| **Foreign-employment exemption s10(1)(o)(ii)** | **R1.25m** cap; **183 full days + 60 continuous days** outside SA in any 12 months; excludes independent contractors & public sector; **s6quat** credit above the cap | ◑ concept present |
| DTA tie-breakers | permanent home → centre of vital interests → habitual abode → nationality | 🔲 |
| CFC (s9D), CRS/AEOI | net-income imputation; automatic info exchange | 🔲 |

---

## 2. Improvement plan for the "Tax Me If You Can" agent

Sequenced by value × reuse of the existing deterministic pattern. Every figure → `sa_rates.py` (dated, SARS-cited) before shipping; LLM narrates only.

### Tier A — Calculation completeness (highest near-term value; reuses the income_tax/vat pattern)
- **A1 `services/cgt.py`** — CGT for individuals + companies: inclusion 40%/80%, annual exclusion R50,000, primary-residence R3m, small-business-asset exclusion, base-cost. Reused by exit-tax (D2).
- **A2 `services/fringe_benefits.py`** — company car (3.5%/3.25%), low-interest loan (official rate 7.75%), accommodation.
- **A3 `services/lump_sum.py`** — retirement + severance tables, R550k tax-free, cumulative-lifetime aggregation.
- **A4 assessed losses** — s20 company cap (R1m/80%) + s20A individual ring-fencing; extend `income_tax`/a company module.
- **A5 turnover tax (6th Sch)** — graduated table; compare vs normal/SBC.
- **A6 travel** — add the SARS deemed-cost **fixed-cost table** (by vehicle value) as a second method + subsistence R595/R184.
- **A7 `services/sars_penalties.py`** — admin penalty (s211 table), **USP behaviour table (s223)**, interest (s89), provisional par-27 late penalty. (USP needs a behaviour input; deterministic given the band.)

### Tier B — SARS process & compliance machinery (guidance + deterministic checkers)
- **B1** extend `compliance_calendar.py` with the auto-assessment window, filing-season + dispute deadlines (NOO 80 / NOA 30 / reasons 45 business days).
- **B2 `services/tcs_status.py`** — estimate the **4-pillar** compliance status from known data (registration/submission/debt/relevant-material) → a "SARS good-standing" panel.
- **B3 process-guidance panels** (data-driven, the LLM narrates): verification-vs-audit, the dispute roadmap, debt-relief options (s164/167/200), VDP eligibility, record-keeping (5-yr).
- **B4** a **"SARS next actions"** engine — given the client's state, the concrete deadlines + steps.

### Tier C — Audit-risk intelligence (extend `tax_risk_flags.py`)
- **C1** an **audit-risk score** from concrete signals (IT3/declaration mismatch, low ETR, repeated losses, VAT-refund pattern, cash-vs-turnover, outsized deductions).
- **C2** a **GAAR exposure** check (the s80A four requirements) on flagged arrangements.
- **C3** map each flag → likely **USP behaviour band** (ties C to A7) → a rand exposure range.
- **C4** reportable-arrangement (s34–39) awareness flag.

### Tier D — Cross-border (extend `relocation_tax.py`; the flagship)
- **D1 residency-test engine** — ordinarily-resident + physical-presence (91/91-each/915/330) day-count from a travel log.
- **D2 exit-tax s9H** — deemed-disposal calc (reuses **A1** CGT).
- **D3 foreign-employment exemption s10(1)(o)(ii)** — R1.25m cap + 183/60-day test + s6quat credit.
- **D4** DTA tie-breaker decision-tree + CFC (s9D) + CRS awareness.

**Recommended sequence:** A → C → B → D. A7+C3 together turn the engine from "computes tax" into "computes tax **and** the SARS-exposure around it" — the differentiator. All cross-border (D) keeps the existing "not advice / licensed-adviser hand-off" framing.

### Budget-2026 figure refreshes to apply now (low-effort, high-correctness)
- CGT annual exclusion **R50,000**; primary-residence **R3m** (new).
- Turnover-tax threshold **R2.3m** (engine already has it ✅).
- Official rate of interest **7.75%** (for fringe-benefit loans).
- Confirm the 2026/27 individual brackets/rebates are current (engine reuses `relocation_tax` constants).

---

## 3. Sources (representative; full set in the 2026-06-27 research session)
SARS: Capital Gains Tax; Retirement Lump Sum Benefits; Foreign Employment Income Exemption; Auto-Assessment; Admin Penalty; Objections / Dispute Resolution; Guide for Employers (Fringe Benefits, Allowances); Turnover Tax; Cease to be a Tax Resident; Tables of Interest Rates (Table 3); Budget 2026 FAQ. Plus PwC Tax Summaries, TaxTim, SAIT, Tax Faculty, Cliffe Dekker Hofmeyr, BDO (USP/GAAR commentary). **All figures pending confirmation + dating in `sa_rates.py` before any calc ships.**
