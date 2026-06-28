"""
evidence_pack.py - the pilot "conceptual-soundness" evidence pack for the Imara Score.

Pure assembly; no new computation. The 2026-06-28 research (Thread 1) set the
minimum bar to sell a SHADOW-MODE pilot before any outcome data exists:
  (i)   a documented conceptual-soundness model dossier,
  (ii)  benchmark-convergence evidence (Altman Z''),
  (iii) expert-panel agreement, and
  (iv)  a stated outcome-validation roadmap (Gini>0.40 / AUC>0.70 / KS>0.25).
This packages what Imara ALREADY has - the weighted model logic, the per-firm
Altman-Z'' convergence (distress_score), the model card, the s71(3) disclosure -
into one artifact a lender reads, plus an honest status for each of the four
pillars. It deliberately does NOT claim the Score is "validated"; it is the
collateral that gets the pilot signed so the outcome clock can start.

The full written dossier lives at docs/IMARA_SCORE_MODEL_DOSSIER.md.
"""

# The buyers'-expected outcome-validation targets (research-confirmed practitioner bar).
_TARGETS = {"gini_min": 0.40, "auc_min": 0.70, "ks_min": 0.25,
            "stability_psi_max": 0.10, "sample_goods": 1500, "sample_bads": 2000,
            "performance_window_months": 12}


def build_evidence_pack(report) -> dict:
    """Assemble the pilot evidence pack from an analysis report. Pure."""
    if not isinstance(report, dict):
        return {"available": False, "reason": "No report."}
    comps = [c for c in (report.get("imara_components") or []) if isinstance(c, dict)]
    score = report.get("imara_score")
    if not comps or score is None:
        return {"available": False, "reason": "No Imara Score to evidence."}

    from services.model_card import model_card
    from services.score_disclosure import build_disclosure
    card = model_card()
    disclosure = build_disclosure(report)

    # (ii) benchmark convergence - the independent Altman Z'' cross-check (already computed)
    z = report.get("distress_score") if isinstance(report.get("distress_score"), dict) else {}
    conv = z.get("convergence") if isinstance(z, dict) else None
    if conv and isinstance(conv, dict):
        bench = {"status": "available", "benchmark": "Altman Z'' (EM-score)",
                 "agreement": conv.get("agreement") or conv.get("level"),
                 "statement": conv.get("statement"),
                 "z_zone": z.get("zone"), "imara_band": report.get("imara_band")}
    else:
        bench = {"status": "pending", "benchmark": "Altman Z'' (EM-score)",
                 "statement": "Insufficient financials to compute the independent Z'' cross-check for this firm."}

    pillars = [
        {"pillar": "Conceptual soundness", "status": "documented",
         "evidence": ("Deterministic-first design (every figure computed in code; the LLM only narrates; "
                      "narration verified against the computed figures), the AHP-weighted component model, and "
                      "the full method are documented in the model card + docs/IMARA_SCORE_MODEL_DOSSIER.md.")},
        {"pillar": "Benchmark convergence", "status": bench["status"],
         "evidence": bench.get("statement")},
        {"pillar": "Expert-panel agreement", "status": "pending",
         "evidence": ("Run a blind expert-rating panel on a sample and report agreement vs the Imara Score "
                      "(Ruan-led; the highest-credibility move available pre-outcomes after Z'' convergence).")},
        {"pillar": "Outcome validation", "status": "not_started_cold_start",
         "evidence": ("Not yet outcome-calibrated by design (cold-start, honest). Starts when a shadow-mode "
                      "pilot lands real labelled outcomes; targets below.")},
    ]

    return {
        "available": True,
        "as_of": "pilot evidence pack",
        "headline": ("Imara Score {} (band {} - {}). Decision-support / triage - NOT a validated default "
                     "predictor. This pack is the conceptual-soundness + convergence evidence to support a "
                     "shadow-mode pilot, not a claim of statistical validation.").format(
                         score, report.get("imara_band"), report.get("imara_label")),
        "score": score, "band": report.get("imara_band"),
        "confidence": report.get("imara_confidence"), "completeness_pct": report.get("imara_completeness"),
        "model_logic": disclosure.get("underlying_logic") if isinstance(disclosure, dict) else None,
        "benchmark_convergence": bench,
        "minimum_viable_evidence": pillars,
        "outcome_validation_roadmap": {
            "status": "awaiting shadow-mode pilot outcomes",
            "method": ("Run the Score in shadow / champion-challenger mode on a design-partner lender's book "
                       "(scores live applicants alongside their existing decision, changes nothing, captures "
                       "both) to accrue labelled outcomes - the only path to a true Gini/KS."),
            "targets": _TARGETS,
            "harness_ready": ("outcomes table + services/validation.py (AUC/Gini/KS) + services/"
                              "score_calibration.py (Platt cold-start) + IMARA_PILOT_PROTOCOL.md already built."),
        },
        "model_card": card,
        "disclaimer": ("Pilot collateral. The Imara Score is decision-support, not a credit decision or a "
                       "statistically-validated default model; it has not yet been calibrated against real "
                       "funding/repayment outcomes. Positioned for a shadow-mode pilot, not binding lending."),
    }
