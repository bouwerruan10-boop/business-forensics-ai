"""
score_disclosure.py - POPIA s71(3) explainability + contestability for the Imara Score.

Pure functions for the disclosure; thin DB wrappers for contestation. The 2026-06-28
strategic research (Thread 3) named this the regulatory keystone: a creditworthiness
profile triggers POPIA s71, whose s71(3) safeguards require BOTH (a) "sufficient
information about the underlying logic" AND (b) a route for the data subject to make
representations. `reason_codes.py` already gives the model-true factor attribution
(the "underlying logic" half + NCA s62 dominant-reason + the FSCA SHAP/LIME-equivalent);
this module packages that into one disclosure artifact and adds the missing CONTESTABILITY
half, recorded immutably in the tamper-evident decision-audit hash chain.

Decision-support, not a credit decision or adverse-action notice under the NCA.
"""

from services.reason_codes import reason_codes

# The 8 possible Imara Score components (must mirror ceo_agent._calculate_imara_score),
# so the disclosure can show the data subject which inputs were and were NOT used.
_ALL_COMPONENTS = (
    "Profitability", "Credit Readiness", "Risk & Compliance", "Operational Efficiency",
    "Financial Integrity", "Market Visibility", "Tax Compliance", "Legal Compliance",
)


def build_disclosure(report) -> dict:
    """Assemble the POPIA s71(3) disclosure for the Imara Score. Pure."""
    if not isinstance(report, dict):
        return {"available": False, "reason": "No report."}
    comps = [c for c in (report.get("imara_components") or []) if isinstance(c, dict)]
    score = report.get("imara_score")
    if not comps or score is None:
        return {"available": False, "reason": "No Imara Score components to disclose."}

    contributions = []
    for c in comps:
        w = float(c.get("weight") or 0)
        v = max(0.0, min(100.0, float(c.get("value") or 0)))
        contributions.append({
            "factor": c.get("label"), "value": int(round(v)), "weight_pct": round(w * 100, 1),
            "contribution": round(v * w, 1),   # points this factor adds to the 0-100 score
        })
    contributions.sort(key=lambda x: -x["contribution"])
    used = {c.get("label") for c in comps}
    inputs_used = [{"factor": lbl, "used": lbl in used} for lbl in _ALL_COMPONENTS]

    rc = reason_codes(report)

    return {
        "available": True,
        "as_of": "POPIA s71(3) disclosure",
        "score": score,
        "band": report.get("imara_band"),
        "label": report.get("imara_label"),
        "confidence": report.get("imara_confidence"),
        "completeness_pct": report.get("imara_completeness"),
        "underlying_logic": {
            "method": ("The Imara Score is a deterministic weighted blend of the components below, each 0-100 "
                       "(higher is better). Score = sum(value x weight). Components not produced this run are "
                       "dropped and the remaining weights re-normalised, so the score is always 0-100. Every "
                       "value is computed in code from your data; the AI only narrates - it does not set the score."),
            "components": contributions,
            "normalisation_note": ("Weights shown are the re-normalised (effective) weights for this analysis; "
                                   "{}% of the 8 possible components were produced (confidence: {}).").format(
                                       report.get("imara_completeness", 0), report.get("imara_confidence", "n/a")),
        },
        "principal_reasons": rc.get("reasons", []),
        "strengths": rc.get("strengths", []),
        "inputs_used": inputs_used,
        "your_rights": {
            "decision_support": ("This score is decision-support, not a credit decision. Under POPIA s71 a "
                                 "decision with legal/material effect may not be based SOLELY on automated "
                                 "processing - a human must make any actual lending decision."),
            "make_representations": ("You may contest this score or any factor in it. Lodge a representation and "
                                     "it is recorded in the tamper-evident audit log and reviewed by a human."),
            "underlying_logic_provided": True,
        },
        "disclaimer": ("Explainability + contestability disclosure for the Imara Score, derived directly from the "
                       "score's own weighted components (POPIA s71(3); NCA s62 dominant-reason). Decision-support - "
                       "not a credit decision or adverse-action notice under the National Credit Act."),
    }


def record_contestation(analysis_id, factor="", statement="", contact="", submitted_by="operator") -> dict:
    """Record a data-subject representation against the score, immutably (hash-chained audit log)."""
    from services.database import append_audit
    record = {
        "analysis_id": str(analysis_id or ""),
        "type": "score_contestation",
        "factor": str(factor or ""),
        "statement": str(statement or "")[:4000],
        "contact": str(contact or "")[:300],
        "submitted_by": str(submitted_by or "operator"),
        "status": "lodged",
    }
    res = append_audit(record)
    return {**record, **res}


def list_contestations(analysis_id) -> dict:
    """Return the representations lodged against an analysis, in order, with chain status."""
    from services.database import get_audit
    rows = [r for r in (get_audit(analysis_id) or []) if isinstance(r, dict)
            and r.get("type") == "score_contestation"]
    return {"available": True, "analysis_id": str(analysis_id or ""), "count": len(rows),
            "contestations": rows}
