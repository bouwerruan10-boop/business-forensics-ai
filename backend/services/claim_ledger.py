"""
claim_ledger.py - the report-wide verification manifest ("prove it" at a glance).

Folds the narrative number-check (narrative_claims) together with the EXISTING per-finding
signals (faithfulness, prose_verifier, finding_quality) into one honest summary of how much
of the report is verified against Imara's computed data, how much conflicts, and how much is
an unverified estimate. Pure / deterministic. Optionally written to the tamper-evident audit
hash chain so each report's verification state is immutable and auditable.
"""


def build_claim_ledger(report) -> dict:
    """Assemble the report-wide claim/verification manifest. Pure."""
    if not isinstance(report, dict):
        return {"available": False, "reason": "No report."}
    from services.narrative_claims import verify_narrative

    nar = verify_narrative(report)
    ns = nar.get("summary", {}) if isinstance(nar, dict) else {}
    fs = report.get("faithfulness_summary") if isinstance(report.get("faithfulness_summary"), dict) else {}
    ps = report.get("prose_verifier_summary") if isinstance(report.get("prose_verifier_summary"), dict) else {}
    fq = report.get("finding_quality") if isinstance(report.get("finding_quality"), dict) else {}

    nar_total = int(ns.get("total") or 0)
    nar_verified = int(ns.get("verified") or 0)
    nar_conflicts = int(ns.get("conflicts") or 0)
    nar_unverified = int(ns.get("unverified") or 0)
    finding_conflicts = int(fs.get("conflicts") or 0) + int(fs.get("benchmark_conflicts") or 0)
    prose_flagged = int(ps.get("flagged") or 0)

    total_conflicts = nar_conflicts + finding_conflicts + prose_flagged
    if total_conflicts:
        overall = "conflicts_present"
    elif nar_unverified:
        overall = "unverified_present"
    else:
        overall = "all_clear"

    headline = ("{}/{} narrative figures verified against your computed data; {} conflict(s); "
                "{} findings cross-checked.").format(nar_verified, nar_total, total_conflicts,
                                                     int(fs.get("checked") or 0))

    return {
        "available": True,
        "overall": overall,
        "headline": headline,
        "narrative": ns,
        "narrative_claims": nar.get("claims", []),
        "findings": {"checked": int(fs.get("checked") or 0), "confirmed": int(fs.get("confirmed") or 0),
                     "conflicts": finding_conflicts, "conflict_titles": fs.get("conflict_titles", [])},
        "prose": {"checked": int(ps.get("checked") or 0), "flagged": prose_flagged,
                  "flag_titles": ps.get("flag_titles", [])},
        "quality": {"strong": int(fq.get("strong") or 0), "adequate": int(fq.get("adequate") or 0),
                    "weak": int(fq.get("weak") or 0)},
        "note": ("Every number Imara shows you is checked against its own deterministically-computed values. "
                 "'verified' = matches the computation; 'conflict' = the narrative disagrees with the computed "
                 "figure (review it); 'unverified' = an estimate that can't be traced to a computed figure. "
                 "Imara never silently presents an unverified number as fact."),
        "disclaimer": "Decision-support / verification aid - not a guarantee; confirm material figures.",
    }


def record_claim_ledger(analysis_id, ledger) -> dict:
    """Write a COMPACT ledger summary to the tamper-evident audit chain (no full claim list)."""
    from services.database import append_audit
    ledger = ledger if isinstance(ledger, dict) else {}
    record = {
        "analysis_id": str(analysis_id or ""),
        "type": "claim_ledger",
        "overall": ledger.get("overall"),
        "headline": ledger.get("headline"),
        "narrative": ledger.get("narrative"),
        "findings": ledger.get("findings"),
        "prose": ledger.get("prose"),
        "quality": ledger.get("quality"),
    }
    res = append_audit(record)
    return {"recorded": True, "overall": record["overall"], **res}
