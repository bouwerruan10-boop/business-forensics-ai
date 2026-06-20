# Imara — Model Validation & Calibration Plan

**Diagnosis.** Imara is engineering-mature but evidence-immature. The pipeline is robust and transparent, but the headline **Imara Score is a well-built heuristic, not a validated model**: the component weights (Profitability 0.25, Credit 0.20, Risk 0.15, …) and the ratio→score anchors are expert judgments never tested against real outcomes, and ~55% of the score's weight rests on un-ground-truthed LLM judgment (only *cited figures* are faithfulness-checked, not the *scores*). The fix is evidence, in three layers.

## Layer 1 — Deterministic correctness (DONE, no API, CI-gated)
The deterministic engine (extraction + ratios + fundamentals) is the trustworthy core. It is now validated against an **independent ground-truth golden set of 12 cases** spanning retail, manufacturing, logistics, agriculture, construction, hospitality, SaaS, wholesale, professional services and distressed/strong profiles. Expected ratios are computed by independent formulas, not copied from the engine.
- **Baseline: 100/100 — every case matches ground truth.** Fundamentals rank sensibly (distressed 15 → strong 96).
- Locked in CI (`test_golden_set_expanded_and_deterministic_baseline`), so any extraction/ratio regression fails the build.

## Layer 2 — LLM-judge trust (HARNESS DONE; one paid run to activate)
The LLM-as-judge (Build 2) can only be trusted if it agrees with humans. New `validate_judge()` measures judge-vs-human agreement on a **10-finding human-labelled set** (`evals/judge_labels.json`, 5 strong / 5 weak), targeting **75–90%** before the judge is trusted to grade at scale. Wired into `python -m evals.run_evals --full`.
- **Ruan/Claude action:** run `run_evals --full` once (uses API) to print the agreement %. If <75%, read the disagreements and tighten the rubric (`evals/RUBRIC.md`) — don't "fix" the judge by overfitting.

## Layer 3 — Score calibration against real outcomes (NEEDS YOUR DATA)
This is the step that turns the Score from a defensible heuristic into a *validated bankability predictor*. It cannot be done synthetically — it needs real businesses with known outcomes.
1. **Persist + accumulate.** Attach the Railway Volume (below) so every analysis is retained with its Imara Score + components.
2. **Attach outcomes.** For ≥30–50 real analyses, record a simple outcome label: did they secure the facility / survive 12 months / repay? Even coarse labels work.
3. **Back-test predictive validity.** Measure whether a higher Imara Score actually associates with the good outcome (rank correlation / AUC of score vs outcome). This is the honest test of the model.
4. **Re-fit weights + anchors.** Replace judgment weights with a fit (e.g., logistic regression of components → outcome), keeping the deterministic Profitability anchor. Re-run Layers 1–2 to confirm no regression.
5. **Version the Score.** Bump `SCORE_SCHEMA_VERSION` when weights change so external (lender) consumers can pin a version.

## Split of work
**Claude has done (no API, shipped):** Layer 1 (12-case ground-truth golden set + 100% baseline, CI-gated) and the Layer 2 harness (`validate_judge` + labelled set + runner wiring) + this plan.
**Ruan must do:** (a) attach the Railway Volume (gates Layer 3 and prevents data loss now); (b) optionally set `ADMIN_API_KEY`; (c) run `run_evals --full` once to print judge agreement; (d) over time, supply real outcome labels so Claude can run the Layer-3 back-test and re-fit the weights.
