"""
claim_ledger.py - the report-wide verification manifest ("prove it" at a glance).

Folds the narrative number-check (narrative_claims) together with the EXISTING per-finding
signals (faithfulness, prose_verifier, finding_quality) into one honest summary of how much
of the report is verified against Imara's computed data, how much conflicts, and how much is
an unverified estimate. Pure / deterministic. Optionally written to the tamper-evident audit
hash chain so each report's verification state is immutable and auditable.

Phase 3 adds the `assurance` roll-up: ONE honest trust metric over every claim in the report
(narrative + finding figures) - coverage %, average calibrated confidence, and a FAIL-CLOSED
contract check that no claim escaped without {verification, confidence, explanation}. A claim
that leaks the contract forces the report out of any "clear" state (fail-closed by design).
"""


def _assurance(all_claims):
    """Report-wide trust roll-up over every claim + the fail-closed contract check. Pure."""
    claims = [c for c in (all_claims or []) if isinstance(c, dict)]
    total = len(claims)
    verified = sum(1 for c in claims if c.get("verification") == "verified")
    conflicts = sum(1 for c in claims if c.get("verification") == "conflict")
    unverified = sum(1 for c in claims if c.get("verification") == "unverified")
    confs = [c.get("confidence") for c in claims if isinstance(c.get("confidence"), (int, float))]
    avg_conf = round(sum(confs) / len(confs), 2) if confs else None
    coverage = round(100.0 * verified / total, 1) if total else 100.0
    # FAIL-CLOSED: every claim must carry the full contract; any that doesn't is a "leak".
    leaks = [str(c.get("text", ""))[:60] for c in claims
             if c.get("verification") not in ("verified", "conflict", "unverified")
             or not isinstance(c.get("confidence"), (int, float))
             or not c.get("explanation")]
    return {
        "total_claims": total, "verified": verified, "conflicts": conflicts,
        "unverified": unverified, "coverage_pct": coverage, "avg_confidence": avg_conf,
        "contract_enforced": not leaks, "leaks": leaks[:10],
        "statement": ("{} of {} numbers shown are traced to your computed data; {} flagged as "
                      "estimates; {} need review.").format(verified, total, unverified, conflicts),
    }


def build_claim_ledger(report) -> dict:
    """Assemble the report-wide claim/verification manifest. Pure."""
    if not isinstance(report, dict):
        return {"available": False, "reason": "No report."}
    from services.narrative_claims import verify_narrative, verify_finding_figures

    nar = verify_narrative(report)
    ns = nar.get("summary", {}) if isinstance(nar, dict) else {}
    ffr = verify_finding_figures(report)
    ffs = ffr.get("summary", {}) if isinstance(ffr, dict) else {}
    fs = report.get("faithfulness_summary") if isinstance(report.get("faithfulness_summary"), dict) else {}
    ps = report.get("prose_verifier_summary") if isinstance(report.get("prose_verifier_summary"), dict) else {}
    fq = report.get("finding_quality") if isinstance(report.get("finding_quality"), dict) else {}

    nar_total = int(ns.get("total") or 0)
    nar_verified = int(ns.get("verified") or 0)
    nar_conflicts = int(ns.get("conflicts") or 0)
    nar_unverified = int(ns.get("unverified") or 0)
    ff_checked = int(ffs.get("checked") or 0)
    ff_verified = int(ffs.get("verified") or 0)
    ff_unverified = int(ffs.get("unverified") or 0)
    finding_conflicts = int(fs.get("conflicts") or 0) + int(fs.get("benchmark_conflicts") or 0)
    prose_flagged = int(ps.get("flagged") or 0)

    assurance = _assurance(list(nar.get("claims", [])) + list(ffr.get("claims", [])))

    total_conflicts = nar_conflicts + finding_conflicts + prose_flagged
    if total_conflicts or not assurance["contract_enforced"]:   # fail-closed: a contract leak forces review
        overall = "conflicts_present"
    elif nar_unverified or ff_unverified:
        overall = "unverified_present"
    else:
        overall = "all_clear"

    headline = ("{}/{} narrative figures verified against your computed data; {} conflict(s); "
                "{} findings cross-checked; {}/{} finding figures traced.").format(
                    nar_verified, nar_total, total_conflicts, int(fs.get("checked") or 0),
                    ff_verified, ff_checked)

    return {
        "available": True,
        "overall": overall,
        "headline": headline,
        "assurance": assurance,
        "narrative": ns,
        "narrative_claims": nar.get("claims", []),
        "finding_figures": {"checked": ff_checked, "verified": ff_verified, "unverified": ff_unverified},
        "finding_figure_claims": ffr.get("claims", []),
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
        "assurance": ledger.get("assurance"),
        "narrative": ledger.get("narrative"),
        "finding_figures": ledger.get("finding_figures"),
        "findings": ledger.get("findings"),
        "prose": ledger.get("prose"),
        "quality": ledger.get("quality"),
    }
    res = append_audit(record)
    return {"recorded": True, "overall": record["overall"], **res}
