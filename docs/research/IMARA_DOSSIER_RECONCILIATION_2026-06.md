# Imara Master Dossier — Build-State Reconciliation (2026-06-29)

Ruan supplied an external "Master Dossier" (23 evidence-backed market claims · 23 red-team
risks · 23 paired solutions). This doc reconciles its 23 weaknesses against Imara's **actual
codebase**, via four parallel code audits. Evidence-first: every verdict is file-cited.

## Headline
The dossier is a strong external analysis but **understates how much is already built**. Of 23
weaknesses: ~10 already shipped & live, ~8 PARTIAL (bounded fixes), **1 genuinely missing
capability (M2 alt-data)**, the rest activation or Ruan-led. **None of the 4 "CRITICAL" items is
a green-field build** — each is awaiting the pilot or one bounded module. The binding constraint
remains Tier-0: a design partner feeding real labelled outcomes.

## Verdict table (with code evidence)

| ID | Dossier risk | Verdict | Evidence (file) |
|----|----|----|----|
| E1 | Score unvalidated vs real defaults | BUILT-IDLE (needs pilot) | `services/validation.py` (AUC/Gini/KS), `outcomes` table, `/api/admin/validation`, admin `ScoreValidationPanel` — 149 local rows are synthetic seed |
| E2 | Garbage-in / unverified docs | BUILT-ACTIVE; residual open-banking feed | `services/statement_integrity.py` (forward-balance reconcile + PDF-tamper), `bank_signals.py`; gap = no third-party feed, no hard gate |
| E3 | Score doesn't create cash/collateral | ADDRESSED (channel built) | `services/funder_gates.py` (SEDFA/SEFA/IDC/NEF gates), `funding_fit.py` |
| E4 | LLM narrative confidently wrong | BUILT-ACTIVE (minus formal sign-off) | `faithfulness.py`, `prose_verifier.py`, `claim_ledger.py` fail-closed, `evals/run_evals.py`+`grader.py` judge-gate, `audit_log.py`+`database.py` hash chain |
| E5 | Calibration drift / no monitoring | PARTIAL | `fleet_quality.py` operational drift LIVE; PSI/realised-vs-predicted MISSING (buildable) |
| M1 | TAM overstated | PARTIAL/Ruan | top-down sourced (`docs/research/...`, `IMARA_LENDER_CHANNEL_KIT.md`); no bottom-up SOM doc |
| M2 | Formal-only ignores informal | **MISSING** | no alt-data scoring path; thin-file → `available:False`. The one real capability gap |
| M3 | Tiny SA TAM | PARTIAL | `country` column + `/api/v1` + `score_contract.py` exist; engine SA-specific |
| M4 | Macro suppresses lending | BUILT-ACTIVE | `funder_gates.py` counter-cyclical DFI targeting |
| C1 | Chicken-and-egg / shadow | PARTIAL (needs pilot+flag) | shadow path supported (`external_score` outcome type); no first-class `shadow` flag |
| C2 | Incumbents have data | PARTIAL | moat seams built/unfed: `outcomes`, `owner` column, `/api/v1`; no cross-tenant CRD |
| C3 | Wants validated PD | BUILT-IDLE (needs pilot) | `services/score_calibration.py` (Platt/PD, honest N≥50 cold-start), `/api/admin/calibration` |
| C4 | Low IP moat | PARTIAL | IP defence ACTIVE (gitleaks hard-gate, trade-secret LICENSE, `input_guard.py`); data moat unfed |
| D1 | NCA affordability law | PARTIAL | per-decision audit record BUILT (`audit_log.py`, `tax_audit_trail.py`); formal Reg 23A calc MISSING |
| D2 | POPIA §71 automated decisions | BUILT-ACTIVE (strongest) | `score_disclosure.py` (disclosure+contestation), `reason_codes.py`, `ScoreReasons.jsx`, `/contest` |
| D3 | "Not advice" shield | BUILT-ACTIVE | `governance.py` (NCA/POPIA/FAIS s1(3)(a)), applied across report/exports/model-card |
| H1 | Algorithmic bias / disparate-impact | PARTIAL/MISSING | proxy-exclusion stance + honest "deferred" in `model_card.py`; no real disparate-impact test |
| H2 | Over-indebtedness | BUILT-ACTIVE | `lender_view.py` max-serviceable-debt + DSCR; gearing/interest-cover/distress flags |
| H3 | Private gatekeeper | BUILT-ACTIVE | decision-support framing + reason codes + appeal route |
| H4 | Re-encodes owner proxy | BUILT-ACTIVE (prevented) | `ceo_agent._calculate_imara_score` 8 components 100% business-level; `owner_risk.py` excluded from Score |
| O1 | Single-founder | RUAN-LED | non-code; `HANDOFF.md`/`CLAUDE.md` strong |
| O2 | Blind spots / SPOF | BUILT-DORMANT (need keys) | `obs.py` (structlog+Sentry), `backup.py` (BACKUP_ENABLED), persistence self-diagnosis; gap = deploy redundancy |
| O3 | Copyable SaaS | BUILT-ACTIVE | gitleaks CI hard-gate, proprietary trade-secret LICENSE, `input_guard.py` |

## The three buckets

**Activate (minutes, Ruan):** set `SENTRY_DSN` + `BACKUP_ENABLED` (O2); promote dep-audit to blocking (O3).

**Build now (Claude, bounded, no partner) — recommended order:**
1. Reg 23A affordability record (D1) — `services/affordability.py` → audit chain. The only "critical" that's a real build gap.
2. Applicant-facing adverse-action reason letter (H3/D2) — fold `reason_codes`+`build_disclosure` into an exportable letter.
3. Disparate-impact / 80%-rule fairness metric (H1) — `services/fairness.py` → model card.
4. Validation-harness completion (E5+C1) — PSI/realised-vs-predicted in `validation.py` + first-class `shadow` flag.
5. Locks + SOM: tests asserting Score never gains an owner term (H4) and every export carries the advice shield (D3); bottom-up SOM doc (M1).
6. Alt-data overlay (M2) — the one genuinely missing capability; phase after the above.

**Ruan-led (Tier-0, the real unlock):** sign one design partner → feeds outcomes → converts the idle validation/PD/calibration spine (E1, C3, real-C1/E5, C2/C4 moat) into real out-of-sample Gini/PD. Plus SA credit-law legal opinion (D1/D3) and team build-out (O1).

## Note: market-claim corrections (doc/marketing, not code)
The dossier's own Corrections Checklist (G2b, G7, DM2, DM3, SA1, SA4, G5, G6, SAR5) applies to
external marketing copy, not the codebase — fold into any investor/lender materials before use.
