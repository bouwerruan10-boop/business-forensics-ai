# Imara — Portable Evidence Research & Decision (2026-06-28)

**Question researched:** Now that the deterministic "prove it" claim/evidence contract is complete
(every user-facing number verified vs computed data, marked verified / conflict / unverified with a
calibrated confidence band and a report-wide assurance roll-up), what is the single highest-value,
buildable next action? Run a research cycle, then execute the best one.

Two cited research threads (external) plus an internal codebase audit.

---

## Thread 1 — What lenders / regulators require in 2026

- **The wedge has moved from "explainable" to "provable + audit-ready that travels with the artifact."**
  Grounded/explainable AI is now *table-stakes as a claim* (Sage+PwC "glass box", Hebbia, CFA Institute
  2025 all converge), but only ~42% of finance teams are "assurance-ready" (KPMG, May 2026), and
  audit-evidence-capable firms see 3–6× better outcomes. Buyers' #1 barrier is hallucinated/numerical
  error (Bloomberg UK finance survey, Jan 2026: 50% named it #1; 32% said source-attribution gives the
  most confidence). LLMs demonstrably fail on financial numbers (FinanceBench: GPT-4-Turbo+retrieval
  81% wrong/refused). → **Provable correctness is the live differentiator, not a better black-box number.**
- **The lender must satisfy *their own* obligations from the vendor's artifact:**
  - **US SR 26-2** (superseded SR 11-7, 17 Apr 2026) & **UK PRA SS1/23**: vendor/third-party model
    documentation must be *sufficient for the buyer's own validation*.
  - **Adverse action — the "specific/dominant reason" standard:** US ECOA 15 USC §1691(d) / Reg B
    12 CFR §1002.9 (a score is insufficient; covers SME credit, delivery relaxed >$1M rev); CFPB
    Circulars 2022-03 & 2023-03 ("no special exemption for AI"; checklist reasons that don't reflect the
    true driver violate ECOA); **SA NCA s.62** (written "dominant reason" on request).
  - **EU AI Act** credit scoring = high-risk (Annex III §5(b)); Arts 12 (logging ≥6mo), 13 (instructions/
    accuracy/limits), 14 (human oversight), **86 (right to explanation, on the deployer, from 2 Aug 2026)**.
  - **SA POPIA s.71**: no decision based *solely* on automated processing of creditworthiness without
    letting the subject make representations + giving "sufficient information about the underlying logic."
  - **SA FSCA/PA AI snapshot (28 Nov 2025)** explicitly flagged the consumer-disclosure gap for automated
    decisions.
- **Honest boundary [inference]:** no source mandates that evidence be *physically embedded in the
  exported PDF*. The legal requirement is decision-level, reproducible, reason-coded evidence bound to
  each output. "Explainability that travels with the artifact" is therefore an **emerging best-practice /
  diligence differentiator**, not (yet) a codified mandate — but it is exactly what the buyer needs to
  discharge the duties above without extra work.

## Thread 2 — Competitive: who surfaces verification to the *recipient*?

- **No comparable tool surfaces per-number verified/conflict/unverified status on the artifact the
  recipient receives.** Verification is built for the analyst *inside* the tool, then a clean narrative
  is shipped.
  - **Fathom** (closest competitor) markets "symbolic attribution" — hover any figure for source/calc —
    but framed explicitly *analyst-side, pre-share* ("before you share… you can verify"); no evidence it
    survives into the exported PDF/shared link.
  - Numeric, Digits, Puzzle, Basis, Ramp: in-app / auditor-facing only.
  - Credit-decisioning vendors (Zest, Taktile, Scienaptic, Rich Data Co) *are* recipient-facing — but
    only because ECOA/FCRA force a *reason-code* (decision-level, not number-level), framed as compliance
    overhead, aimed at examiners.
  - Bridgement (SA): no published explainability layer.
- **Verdict:** recipient-facing, **export-surviving** number verification is **genuine open whitespace**.
  The defensible moat is the export-surviving rendering *plus the explicit conflict/unverified states* —
  and a competitor is "one product decision away," so move fast.

## Thread 3 — Internal codebase audit

- The "prove it" contract (`claim_ledger`: assurance, coverage %, conflicts, unverified, per-claim
  confidence) renders on the **operator Dashboard** and the **web shared link** (`SharedReport` reuses
  `Dashboard` → `VerificationBanner`).
- **The PDF export (`services/report_generator.py`) and HTML export (`services/html_report.py`) contain
  ZERO verification content** — the downloadable, emailable artifact that actually reaches a lender's
  credit committee carries none of it. The differentiator does not travel to the decision-maker.

---

## Decision

**Make the verification / assurance contract travel onto the exported artifact — PDF first (the
lender-facing document via the `banker` audience), then HTML.** It is the convergence of all three
threads: the #1 competitive whitespace, the thing 2026 lender buyers actually need to discharge their
own model-validation / adverse-action / POPIA duties, and a concrete internal gap. It is deterministic
(reuses the existing `claim_ledger`), additive, and changes no agent prompt (no live A/B gate).

**This increment:** a "Verification & Evidence" section in the PDF rendering the assurance roll-up
(overall state, coverage %, avg confidence, plain statement), the conflicts list, and a sample of
unverified estimates with explanations + a "how to read this" note — placed prominently after the Imara
Score. Mirror it in the HTML export.

**Natural follow-on (not this increment):** fold the existing `reason_codes.py` (factor attribution) +
`score_disclosure.py` (POPIA s.71(3) per-factor contribution + contestability) into the same exported
artifact as an adverse-action / "dominant reason" panel — directly satisfying ECOA / NCA s.62 / EU AI
Act Art. 86 from the document itself.

*Sources: EU AI Act Arts 12/13/14/86 + Annex III §5(b) (artificialintelligenceact.eu); POPIA s.71
(popia.co.za); NCA s.62 (Act 34/2005); CFPB Circulars 2022-03 & 2023-03; ECOA/Reg B 12 CFR §1002.9;
SR 26-2 (federalreserve.gov, 17 Apr 2026); PRA SS1/23; FSCA/PA AI snapshot (28 Nov 2025); Bloomberg,
KPMG (May 2026), Sage/IDC, Deloitte, insightsoftware surveys; Patronus FinanceBench; Fathom Commentary
Writer + AI-reporting guide; Hebbia/Cambridge 2026. Inferences flagged inline.*
