"""
Imara Score model card — a machine-readable governance "nutrition label".
Pulls the live AHP weight derivation + governance framing so the card never drifts
from the running system. Served at GET /api/v1/model-card and mirrored in MODEL_CARD.md.
"""
from services.ahp import imara_weight_derivation, PRODUCTION_WEIGHTS
from services.governance import decision_support_notice

MODEL_CARD_VERSION = "1.0"


def model_card() -> dict:
    ahp = imara_weight_derivation()
    return {
        "model": "Imara Score™",
        "card_version": MODEL_CARD_VERSION,
        "owner": "Imara",
        "as_of": "2026-06",
        "summary": ("A 0–100 bankability / investability rating for South African SMEs, produced "
                    "by a deterministic financial engine plus LLM specialist agents, framed as "
                    "decision-support for lenders and investors."),
        "intended_use": decision_support_notice(),
        "out_of_scope": [
            "Consumer (individual) credit scoring.",
            "An automated lending decision or creditworthiness determination.",
            "Use without a human credit analyst or outside an NCA affordability assessment.",
            "Markets or sectors outside SA SMEs without re-validation.",
        ],
        "method": {
            "design": ("Deterministic-first: figures and ratios computed by arithmetic; LLM agents "
                       "narrate and flag, never invent numbers; figures cross-checked (faithfulness)."),
            "scoring": "Weighted composite of up to 8 components, re-normalised over those produced.",
            "weight_derivation": ahp,
            "production_weights": PRODUCTION_WEIGHTS,
            "external_anchor": ("Altman Z''-score (emerging markets) computed independently as a "
                                "convergent-validity cross-check on the Score."),
            "explainability": "Deterministic reason codes — principal factors ordered by impact.",
        },
        "evaluation": {
            "deterministic_golden_set": "12/12 ratio cases correct by independent formulas (CI gate).",
            "llm_judge_agreement": ("100% agreement with human labels on clear-cut findings "
                                    "(target 75–90%; borderline labels to be added to discriminate)."),
            "external_convergence": "Z'' distress zone vs Imara band reported per analysis.",
            "online_monitoring": "Fleet Quality drift monitor over persisted analyses.",
        },
        "fairness": {
            "protected_proxy_controls": ("B-BBEE status (race-linked) is EXCLUDED from the Score and "
                                         "treated as informational / commercial context only."),
            "known_proxy_risks": ("Industry and region carry indirect signal and are monitored. "
                                  "Alternative-data inputs (e.g. bank statements) are surfaced as "
                                  "decision-support, not silent Score inputs."),
            "disparate_impact_testing": ("Proxy-based four-fifths-rule monitoring on the Score band across "
                                         "industry and region is computed on demand at GET /api/admin/fairness. "
                                         "Outcome-validated disparate-impact (on funding/repayment) is deferred "
                                         "until enough real labelled outcomes accumulate."),
        },
        "limitations": [
            ("Weights are AHP/expert-derived and the LLM components are NOT YET calibrated against real "
             "funding/repayment outcomes — a structured heuristic, not an empirically-fitted PD model."),
            "Thin-file inputs (P&L only, no balance sheet) reduce coverage; Z'' then reports 'needs balance sheet'.",
            ("LLM narrative can err; mitigated by deterministic numbers + faithfulness cross-check + "
             "finding-quality critique."),
        ],
        "governance": decision_support_notice(),
    }
