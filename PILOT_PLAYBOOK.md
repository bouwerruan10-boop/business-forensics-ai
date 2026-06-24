# Imara Design-Partner Pilot Playbook — calibrating the Score against real outcomes

**Why this is the priority.** Imara's engineering is done (459 tests, deployed, secured, 18-lever tax engine, 2026/27-current corpus). The one thing standing between Imara and credibility with lenders/investors is that **the Imara Score is still an expert prior — it has never been validated against what actually happened to real businesses.** This pilot fixes exactly that, using the admin tooling now built (record-outcome + bulk CSV import + the Score-validation panel).

**The goal in one line:** collect ~20–50 real SME outcomes (funded / declined / repaid / defaulted) and let the validation panel show whether a low Imara Score actually predicts a bad outcome (AUC/Gini/KS), then calibrate.

---

## How much data you need (matches the panel thresholds)
- **≥ 20 labelled outcomes with both classes** → the panel starts showing **discrimination**: AUC, Gini, KS. *(AUC 0.5 = no skill, 0.7+ = useful, 0.8+ = strong; Gini = 2·AUC − 1.)*
- **≥ 50 labelled outcomes** → **PD calibration** appears (Platt slope ~1 ideal, Brier skill > 0).
- Until then, the **Z'' proxy AUC** in the panel gives interim convergent-validity signal (Imara Score vs the independent Altman Z'' distress model) — useful today, but it is a proxy, not real outcomes.

You do **not** need new customers for this — **historical** cases with known outcomes are ideal (faster, no waiting on repayment).

---

## Who to approach (2 archetypes — one is enough to start)
1. **An SME accountant / bookkeeping firm.** They hold many SMEs' financials *and* informally know who got funded, declined, or went under. One firm can yield 20–40 historical cases in a week. Pitch: "Run your last ~30 SME clients through Imara; I'll show you a bankability score per client and we'll check it against what actually happened to them."
2. **A lender-side contact** (SEDFA/IDC/NEF intermediary, a bank SME credit desk, or a fintech lender). They hold the *outcome* truth (funded / declined / default). Pitch: "Score a sample of your past applicants; let's see if the Imara Score separates the ones that defaulted from the ones that repaid."

The dual-sided sweet spot: an accountant supplies the businesses + documents; a lender contact (or the accountant's own knowledge) supplies the outcomes.

---

## The 4-week protocol
- **Week 1 — assemble + run.** Pick **20–40 real SMEs with a KNOWN outcome** in the last ~24 months. For each, run Imara (intake form + their financials) → record the resulting **Imara Score** and the **analysis_id** (shown in the admin history list, first 8 chars; the full id is in the URL / report).
- **Week 2 — label the outcomes.** For each analysis, decide the binary label:
  - **label = 1 (bad):** declined for funding **or** funded-then-defaulted/in-arrears.
  - **label = 0 (good):** funded and repaying / repaid cleanly.
  - Optionally also capture a `value` (e.g. a bureau score) and `source`.
- **Week 3 — enter outcomes.** Use the admin **Score-validation panel**: record one at a time, or paste a CSV into **Bulk import** (format below).
- **Week 4 — read the evidence + decide.** Open the panel:
  - Real-outcome **AUC ≥ 0.7** → the Score genuinely discriminates → this is the credibility artifact to show lenders/investors.
  - **AUC 0.6–0.7** → promising but recalibrate (adjust the Score component weights; the harness + reliability table show where it's mis-ranking).
  - **AUC < 0.6** → the Score needs rework before external claims; the pilot just saved you from over-claiming.

---

## What to capture per business — bulk CSV format
Paste straight into the admin panel's **Bulk import (CSV)** box, one row per outcome:

```
analysis_id,outcome_type,label,value,source
3f2a…(full id),funded,0,640,Nedbank
9c81…,declined,1,,Absa
b7d4…,default,1,510,client-reported
55ea…,repaid,0,,accountant
```

- `outcome_type`: `funded` | `declined` | `repaid` | `default` | `external_score`
- `label`: `0` = good, `1` = bad/default (this is what discrimination/calibration use)
- `value`: optional number (e.g. bureau score) — leave blank if none
- `source`: optional free text (who reported it)

Unknown/typo'd analysis ids are skipped and reported, so a partly-messy paste still lands the good rows.

---

## What success unlocks
A real-outcome **AUC in the 0.7–0.8 range on even 30–50 cases** is the single most valuable asset Imara can have: it turns "we think the Score is useful" into "here is the measured discrimination on real SA SME outcomes." That is:
- the credibility needed to approach **B2B lenders** (the distribution channel), and
- the evidence that justifies charging for the Score, and
- the input that lets the calibration engine convert the Score into a defensible **probability of distress**.

Everything else is already built and waiting on this.

---

*Honest caveats: early-n results are noisy — keep collecting past 50; ensure both outcome classes are represented; a pilot AUC is indicative, not a published validation. The point is directional evidence to steer the Score and open the lender conversation.*
