"""
tcs_status.py - deterministic SARS Tax Compliance Status (TCS) readiness check.

Pure functions; the LLM only narrates. SARS expresses tax compliance across FOUR
pillars (the "My Compliance Profile" on eFiling), and a TCS PIN is only issued
"Compliant" when all four are green:
  1. Registration - registered for every tax type the business is liable for;
  2. Submission   - no outstanding returns;
  3. Debt         - no outstanding tax debt (or it is under a payment arrangement);
  4. Relevant material - no outstanding information/returns SARS has requested.

A non-compliant TCS blocks tenders, B-BBEE good standing, and a lot of financing -
so this is a bankability signal, not just admin. Imara can DERIVE the registration
pillar from the profile it already holds (e.g. turnover over R1m but not VAT-
registered = a real compulsory-registration gap). It does NOT have deterministic
visibility of outstanding returns / debt, so those pillars are returned as
"verify" (check your eFiling MCP) rather than a fabricated pass - honest by design.
Decision-support / awareness, not a legal determination; not an Imara Score input.
"""

import math
import re

VAT_COMPULSORY_THRESHOLD = 1_000_000   # VAT Act s23 - compulsory once 12-month turnover exceeds R1m
SDL_PAYROLL_FLOOR = 500_000            # Skills Development Levy registration floor
_SDL_AVG_SALARY = 70_000               # rough per-head annual cost, to proxy the SDL floor


def _n(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v if isinstance(v, (int, float))
                  else str(v).strip().replace(" ", "").replace(",", "").replace("R", ""))
    except (ValueError, TypeError):
        return None
    # reject non-finite (inf/nan) so a hostile figure can't crash int() downstream
    return f if math.isfinite(f) else None


def _required_registrations(rev, headcount, vat_reg, is_company):
    """The tax types this profile is liable to be registered for, with whether we
    can already see it satisfied. Returns list of (tax, required, satisfied, note)."""
    out = []
    # Income tax - any company; an individual/other trading entity also files, but
    # we only assert it for a company where it is unambiguous.
    if is_company:
        out.append(("Income Tax", True, True,
                    "A registered company is automatically an income-tax taxpayer."))
    # VAT
    vat_satisfied = vat_reg in ("yes", "true", "registered")
    if rev is not None and rev >= VAT_COMPULSORY_THRESHOLD:
        out.append(("VAT", True, vat_satisfied,
                    "Turnover exceeds R1m - VAT registration is COMPULSORY (VAT Act s23)."))
    elif vat_satisfied:
        out.append(("VAT", True, True, "Already VAT-registered - keep VAT201 current."))
    # PAYE / UIF (employer)
    if headcount and headcount > 0:
        out.append(("PAYE / UIF (employer)", True, None,
                    "You have employees - you must be registered as an employer for PAYE and UIF."))
        if headcount * _SDL_AVG_SALARY >= SDL_PAYROLL_FLOOR:
            out.append(("SDL", True, None,
                        "Payroll likely exceeds ~R500k - SDL registration applies."))
    return out


def build_tcs_status(report) -> dict:
    """Assess SARS TCS readiness across the four pillars from the profile. Pure."""
    if not isinstance(report, dict):
        return {"available": False, "reason": "No report."}

    rev = _n(report.get("annual_revenue")) or _n((report.get("financial_figures") or {}).get("revenue"))
    headcount = int(_n(report.get("headcount")) or 0)
    vat_reg = str(report.get("vat_registered") or "unknown").lower()
    entity = str(report.get("entity_type") or "").lower()
    cipc = str(report.get("cipc_number") or "").strip()
    is_company = ("pty" in entity or "ltd" in entity or "company" in entity
                  or bool(re.match(r"^\s*\d{4}/", cipc)))

    if rev is None and headcount <= 0 and not is_company and vat_reg not in ("yes", "no", "true", "false", "registered"):
        return {"available": False, "reason": "Not enough profile data to assess TCS readiness."}

    # optional explicit signals (forward-compatible: intake/agent may populate these)
    signals = report.get("tcs_signals") if isinstance(report.get("tcs_signals"), dict) else {}

    # --- Pillar 1: Registration (derivable) ---
    reqs = _required_registrations(rev, headcount, vat_reg, is_company)
    gaps = [r for r in reqs if r[1] and r[2] is False]
    if gaps:
        reg_status = "action"
        reg_msg = "Compulsory registration gap: " + ", ".join(g[0] for g in gaps) + "."
    else:
        reg_status = "pass"
        reg_msg = "No registration gap detected from your profile."

    def _signal_pillar(key, default_msg, fail_msg):
        val = signals.get(key)
        if val in (None, "", "unknown"):
            return {"status": "verify", "detail": default_msg}
        bad = bool(val) if isinstance(val, bool) else (_n(val) or 0) > 0
        return {"status": "action" if bad else "pass",
                "detail": fail_msg if bad else "No issue reported."}

    pillars = {
        "registration": {
            "status": reg_status, "detail": reg_msg,
            "required": [{"tax": t, "satisfied": s} for (t, _req, s, _note) in reqs],
        },
        "submission": _signal_pillar(
            "outstanding_returns",
            "Check your eFiling My Compliance Profile (MCP) - any outstanding ITR14/VAT201/EMP201/IRP6 turns this red.",
            "Outstanding returns reported - file every overdue return to clear this pillar."),
        "debt": _signal_pillar(
            "tax_debt",
            "Check your MCP for outstanding tax debt; if any exists, settle it or arrange a deferral so it does not block your TCS.",
            "Outstanding tax debt reported - settle it or put it under an arrangement (s167) to restore good standing."),
        "relevant_material": _signal_pillar(
            "outstanding_relevant_material",
            "Confirm SARS has no outstanding requests for information/relevant material against you.",
            "SARS has requested outstanding material - submit it to clear this pillar."),
    }

    statuses = [p["status"] for p in pillars.values()]
    if "action" in statuses:
        overall = "action_required"
        verdict = "At least one pillar needs action before SARS will issue a 'Compliant' TCS."
    elif "verify" in statuses:
        overall = "verify_on_efiling"
        verdict = "No gap detected from your profile, but confirm the submission/debt pillars on your eFiling MCP."
    else:
        overall = "likely_compliant"
        verdict = "All assessable pillars look clear - request your TCS PIN to prove good standing."

    return {
        "available": True,
        "as_of": "SA 2026 (SARS TCS / eFiling MCP)",
        "overall": overall,
        "verdict": verdict,
        "pillars": pillars,
        "why_it_matters": ("A SARS Tax Compliance Status PIN is what tenders, B-BBEE good standing, many "
                           "lenders and the Foreign Investment / emigration processes check. A red pillar "
                           "blocks all of them - clearing it is direct bankability."),
        "how_to_get": ("Request a TCS PIN on SARS eFiling (Tax Status -> Tax Compliance Status -> activate, "
                       "then request a PIN for 'Good Standing'); share the PIN so a third party can verify in real time."),
        "note": ("Computed from your profile (deterministic). The registration pillar is derived; the submission, "
                 "debt and relevant-material pillars must be confirmed on your eFiling MCP - Imara does not have "
                 "live SARS access. Decision-support, not a legal determination."),
    }
