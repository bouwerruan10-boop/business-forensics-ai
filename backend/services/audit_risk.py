"""
audit_risk.py - deterministic SARS audit-likelihood score.

Pure functions; the LLM only narrates. This does NOT introduce new detectors - it
AGGREGATES the structural flags already produced by services/tax_risk_flags.py
(the GAAR / SARS-scrutiny scanner) into a single 0-100 audit-risk indicator with a
band and the ranked contributing drivers. A quantified overlay for the report, so
an owner/lender can see "how exposed am I to a SARS audit" at a glance - it does
NOT feed the Imara Score.

Honest by design: the score reflects only the flags detected from the data
supplied; a low score is not assurance. Decision-support, not a legal conclusion.
"""

# Points each structural flag contributes, by severity.
_WEIGHT = {"high": 28, "medium": 14, "low": 6}

# Score -> band thresholds (lower bound inclusive).
_BANDS = ((65, "high"), (35, "elevated"), (12, "moderate"), (0, "low"))


def _band(score):
    for lo, name in _BANDS:
        if score >= lo:
            return name
    return "low"


def build_audit_risk(report) -> dict:
    """Aggregate report['tax_risk_flags'] into a 0-100 audit-risk score. Pure.

    Accepts the full report dict (reads its 'tax_risk_flags' block) or the
    tax-risk-flags result dict directly.
    """
    if not isinstance(report, dict):
        return {"available": False, "reason": "No report."}

    flags_res = report.get("tax_risk_flags") if "tax_risk_flags" in report else report
    if not isinstance(flags_res, dict) or not flags_res.get("available"):
        return {"available": False, "reason": "No tax-risk scan available (SA taxpayers only)."}

    flags = flags_res.get("flags")
    flags = flags if isinstance(flags, list) else []
    score = 0
    drivers = []
    for f in flags:
        if not isinstance(f, dict):
            continue
        sev = str(f.get("severity", "low")).lower()
        pts = _WEIGHT.get(sev, _WEIGHT["low"])
        score += pts
        drivers.append({"title": f.get("title", "Risk flag"), "severity": sev,
                        "code": f.get("code", ""), "points": pts})
    score = min(100, score)
    drivers.sort(key=lambda d: d["points"], reverse=True)

    band = _band(score)
    verdict = {
        "high": "Multiple strong audit-selection patterns - tighten substance + documentation now.",
        "elevated": "Several structural patterns SARS watches - get the supporting evidence in order.",
        "moderate": "Some structural exposure - document the flagged arrangements so they are defensible.",
        "low": "No material structural audit triggers detected from the data supplied (not assurance).",
    }[band]

    return {
        "available": True,
        "as_of": flags_res.get("as_of"),
        "score": score,
        "band": band,
        "flag_count": len(flags),
        "drivers": drivers,
        "verdict": verdict,
        "note": ("A 0-100 SARS audit-likelihood indicator aggregated from the structural tax-risk flags "
                 "(GAAR ss80A-80L / SARS scrutiny). It reflects only the data supplied - a low score is "
                 "not assurance - and does not affect the Imara Score."),
        "disclaimer": ("Risk-awareness only, not a finding of wrongdoing or tax advice; ensure commercial "
                       "substance + documentation and confirm with a registered tax practitioner."),
    }
