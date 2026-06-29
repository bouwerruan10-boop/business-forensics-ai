"""
Affordability assessment (NCA / Reg 23A-shaped) — deterministic, decision-support.

The National Credit Act 34 of 2005 (ss 78-81; Reg 23A) requires a credit provider to make a
*documented* affordability assessment before extending credit: income available to service debt,
existing debt obligations, the resulting discretionary surplus, and whether a proposed instalment
is serviceable. The dossier (D1) flagged that Imara had only an *indicative* debt-service view
(`lender_view.borrowing_capacity`), not a per-decision affordability RECORD.

This module produces that record from already-computed figures — Adjusted EBITDA (normalisation),
finance costs and debt stock (financial_figures) — and is folded into the tamper-evident decision
audit chain (see services/audit_log.py). It supports a credit provider's own Reg 23A assessment;
it is NOT itself a credit decision and NOT an Imara Score input (FAIS/NCA framing). No figure is
invented — every number is uploaded-or-computed; non-finite values are dropped to stay JSON-safe.
"""
import math

__all__ = ["assess_affordability", "affordability_stamp", "AFFORDABILITY_SCHEMA_VERSION"]

AFFORDABILITY_SCHEMA_VERSION = "1.0"

# Indicative assumptions, stated so a lender can override (kept consistent with lender_view.py).
_TERM_RATE = 0.12       # ~12% p.a. (SA prime-ish, mid-2026)
_TERM_YEARS = 5
_DSCR_PRUDENT = 1.50
_DSCR_GENEROUS = 1.25


def _num(v):
    """Coerce to a finite float (handles 'R1,234', '(1 234)' negatives); junk/None/non-finite -> None."""
    if v is None or isinstance(v, bool):
        return None
    try:
        if isinstance(v, (int, float)):
            f = float(v)
        else:
            s = str(v).strip().replace(" ", "").replace(",", "").replace("R", "").replace("ZAR", "")
            neg = s.startswith("(") and s.endswith(")")
            f = float(s.strip("()"))
            if neg:
                f = -f
    except (ValueError, TypeError):
        return None
    return f if math.isfinite(f) else None


def _annuity_principal(annual_debt_service, rate=_TERM_RATE, years=_TERM_YEARS):
    """Principal supportable by a given annual debt service, as a level-payment annuity."""
    if not annual_debt_service or annual_debt_service <= 0:
        return 0.0
    if rate <= 0:
        return round(annual_debt_service * years, 2)
    factor = (1 - (1 + rate) ** (-years)) / rate
    return round(annual_debt_service * factor, 2)


def assess_affordability(figures, normalization=None, bank=None, proposed_annual_instalment=None):
    """Return a Reg 23A-shaped affordability record. Pure; never raises.

    income available  = prudent Adjusted EBITDA (or EBITDA / operating profit fallback)
    existing service  = finance costs + indicative principal amortisation of debt stock
    surplus           = income available - existing service
    max new service   = income/DSCR - existing service (prudent 1.50 / generous 1.25)
    proposed verdict  = DSCR on (existing + proposed) instalment, if a proposal is supplied
    """
    figures = figures if isinstance(figures, dict) else {}
    normalization = normalization if isinstance(normalization, dict) else {}

    # ── income available to service debt (most prudent available source) ──
    income, income_source = None, None
    for src, val in (("adjusted_ebitda_low", _num(normalization.get("adjusted_ebitda_low"))),
                     ("ebitda", _num(figures.get("ebitda"))),
                     ("operating_profit", _num(figures.get("operating_profit")))):
        if val is not None:
            income, income_source = val, src
            break

    # ── existing debt obligations ──
    interest = _num(figures.get("interest"))
    total_debt = _num(figures.get("total_debt"))
    indicative_principal = round(total_debt / _TERM_YEARS, 2) if (total_debt and total_debt > 0) else None
    existing_service = None
    if interest is not None or indicative_principal is not None:
        existing_service = round((interest or 0.0) + (indicative_principal or 0.0), 2)

    out = {
        "available": income is not None,
        "schema_version": AFFORDABILITY_SCHEMA_VERSION,
        "income_available_for_debt_service": (round(income, 2) if income is not None else None),
        "income_source": income_source,
        "existing_obligations": {
            "finance_costs": (round(interest, 2) if interest is not None else None),
            "debt_stock": (round(total_debt, 2) if total_debt is not None else None),
            "indicative_annual_principal": indicative_principal,
            "existing_annual_debt_service": existing_service,
            "principal_basis": "Indicative straight-line amortisation of the debt stock over %d years "
                               "(the existing loan term is not disclosed in the financials)." % _TERM_YEARS,
        },
        "assumptions": "Indicative only — term loan assumes ~%.0f%% p.a. over %d years; DSCR %.2f "
                       "(prudent) to %.2f (generous). A lender's own terms will differ."
                       % (_TERM_RATE * 100, _TERM_YEARS, _DSCR_PRUDENT, _DSCR_GENEROUS),
        "method": ("Reg 23A-shaped affordability: income available for debt service (prudent Adjusted "
                   "EBITDA) less existing debt service gives the discretionary surplus; the maximum new "
                   "debt service is income ÷ DSCR less existing service. Deterministic — no AI in the numbers."),
        "basis_note": "Supports a credit provider's own NCA s78-81 / Reg 23A affordability assessment. "
                      "Decision-support — NOT a credit decision and NOT an Imara Score input.",
    }

    if income is None:
        out["reason"] = "No income measure (Adjusted EBITDA / EBITDA / operating profit) could be computed."
        return out

    # ── discretionary surplus + capacity for NEW debt ──
    surplus = round(income - (existing_service or 0.0), 2)
    out["discretionary_surplus_for_new_debt"] = surplus
    if income <= 0:
        out["new_debt_capacity"] = {"serviceable": False,
                                    "reason": "Income available for debt service is not positive — no capacity for new debt."}
    else:
        max_total_prudent = income / _DSCR_PRUDENT
        max_total_generous = income / _DSCR_GENEROUS
        new_service_prudent = max(0.0, round(max_total_prudent - (existing_service or 0.0), 2))
        new_service_generous = max(0.0, round(max_total_generous - (existing_service or 0.0), 2))
        out["new_debt_capacity"] = {
            "serviceable": new_service_prudent > 0,
            "max_new_annual_debt_service_prudent": new_service_prudent,
            "max_new_annual_debt_service_generous": new_service_generous,
            "implied_new_principal_prudent": _annuity_principal(new_service_prudent),
            "implied_new_principal_generous": _annuity_principal(new_service_generous),
            "basis": "Income ÷ DSCR less existing debt service, converted to a term-loan principal.",
        }

    # ── verdict on a specific proposed instalment, if supplied ──
    proposed = _num(proposed_annual_instalment)
    if proposed is not None and proposed > 0:
        total_with_proposed = (existing_service or 0.0) + proposed
        dscr = round(income / total_with_proposed, 2) if total_with_proposed > 0 else None
        if income <= 0 or dscr is None:
            verdict = "unaffordable"
        elif dscr >= _DSCR_PRUDENT:
            verdict = "affordable"
        elif dscr >= _DSCR_GENEROUS:
            verdict = "marginal"
        else:
            verdict = "unaffordable"
        out["proposed_instalment_assessment"] = {
            "proposed_annual_instalment": round(proposed, 2),
            "total_annual_debt_service_with_proposed": round(total_with_proposed, 2),
            "dscr_on_proposed": dscr,
            "verdict": verdict,
            "interpretation": {
                "affordable": "Income covers the proposed instalment with a prudent margin (DSCR ≥ %.2f)." % _DSCR_PRUDENT,
                "marginal": "The proposed instalment is serviceable but with a thin margin (DSCR %.2f–%.2f)." % (_DSCR_GENEROUS, _DSCR_PRUDENT),
                "unaffordable": "The proposed instalment is not prudently serviceable on current figures (DSCR < %.2f)." % _DSCR_GENEROUS,
            }[verdict],
        }
    return out


def affordability_stamp(assessment):
    """Compact, hash-chain-friendly summary of an affordability assessment for the decision audit record."""
    a = assessment if isinstance(assessment, dict) else {}
    cap = a.get("new_debt_capacity") or {}
    prop = a.get("proposed_instalment_assessment") or {}
    return {
        "available": bool(a.get("available")),
        "schema_version": a.get("schema_version"),
        "income_available_for_debt_service": a.get("income_available_for_debt_service"),
        "income_source": a.get("income_source"),
        "existing_annual_debt_service": (a.get("existing_obligations") or {}).get("existing_annual_debt_service"),
        "discretionary_surplus_for_new_debt": a.get("discretionary_surplus_for_new_debt"),
        "max_new_annual_debt_service_prudent": cap.get("max_new_annual_debt_service_prudent"),
        "proposed_verdict": prop.get("verdict"),
        "dscr_on_proposed": prop.get("dscr_on_proposed"),
    }
