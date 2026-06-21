"""
The "Lender's-Eye View" — deterministic, decision-support.

Reddit research (r/loansforsmallbusiness, r/smallbusiness, r/PersonalFinanceZA):
lenders decline on CASH FLOW, not credit score, and deals die when "the bank
statements show a different story than the financials". Owners get declined and
never learn why. This module answers, deterministically, the rejection-moment
question: would a lender decline this business, why, and how much could it
plausibly borrow?

Built on bank_signals (cash-flow evidence) + financial_figures + normalization
(adjusted EBITDA). Everything is INDICATIVE decision-support — NOT a credit
decision and NOT an Imara Score input (consistent with the FAIS/NCA framing).
No figure is invented: inputs come from uploaded text or computed arithmetic.
"""

import math

__all__ = ["run_lender_view"]


def _num(v):
    if v is None:
        return None
    try:
        if isinstance(v, (int, float)):
            f = float(v)
        else:
            s = str(v).strip().replace(" ", "").replace(",", "").replace("R", "").replace("ZAR", "")
            neg = s.startswith("(") and s.endswith(")")
            s = s.strip("()")
            f = float(s)
            if neg:
                f = -f
    except (ValueError, TypeError):
        return None
    return f if math.isfinite(f) else None  # reject NaN/inf -> keeps output JSON-compliant


# Indicative assumptions (clearly stated so a lender can override).
_TERM_RATE = 0.12      # ~12% p.a. (SA prime-ish, mid-2026)
_TERM_YEARS = 5
_DSCR_PRUDENT = 1.50
_DSCR_GENEROUS = 1.25


def _annuity_principal(annual_debt_service, rate=_TERM_RATE, years=_TERM_YEARS):
    if annual_debt_service is None or annual_debt_service <= 0:
        return 0.0
    if rate <= 0:
        return round(annual_debt_service * years, 2)
    factor = (1 - (1 + rate) ** (-years)) / rate
    return round(annual_debt_service * factor, 2)


def run_lender_view(figures, bank, normalization, annual_revenue=0.0):
    figures = figures or {}
    bank = bank or {}
    normalization = normalization or {}

    declared_revenue = _num(figures.get("revenue")) or _num(annual_revenue) or None
    bank_ok = bool(bank.get("available"))
    period_months = bank.get("period_months") or 0
    inflow = _num(bank.get("inflow"))
    avg_monthly_deposits = round(inflow / period_months, 2) if (inflow and period_months) else None
    annualized_deposits = round(avg_monthly_deposits * 12, 2) if avg_monthly_deposits else None
    # Deposits are only usable if they are a plausible magnitude vs revenue (guards against
    # statement-parse artefacts such as two columns merging into one giant number).
    deposits_reliable = bool(
        annualized_deposits and (avg_monthly_deposits or 0) < 1e10
        and (not declared_revenue or annualized_deposits <= 50 * declared_revenue))

    risk_points = 0
    reasons = []   # (severity, text, fix)

    # ── 1. Reconciliation: declared revenue vs banked deposits ────────────────
    reconciliation = {"available": False,
                      "reason": "Need both declared revenue and a usable bank statement to reconcile."}
    if declared_revenue and annualized_deposits and not deposits_reliable:
        reconciliation = {"available": True, "direction": "inconclusive",
                          "declared_revenue": round(declared_revenue, 2),
                          "annualized_deposits": annualized_deposits, "material": False,
                          "interpretation": "Captured bank deposits look implausible versus declared "
                          "revenue (the statement is likely partial or could not be fully read), so this "
                          "was not used as a red flag."}
    elif declared_revenue and annualized_deposits:
        gap = (annualized_deposits - declared_revenue) / declared_revenue
        material = abs(gap) > 0.25
        if gap < -0.90:
            # Deposits ~zero vs revenue almost always means the statement text was
            # partial/unparseable, not literally no income. Do NOT accuse on an artifact.
            direction = "inconclusive"
            interp = ("Captured bank deposits are implausibly low versus declared revenue — the statement "
                      "text is likely incomplete or could not be fully read, so this was not used as a red flag.")
            fix = "Upload clearer/complete bank statements (a text-based PDF or CSV) so deposits can be reconciled."
            material = False
        elif gap < -0.25:
            direction = "deposits_below_revenue"
            interp = ("Banked deposits are well below declared revenue — revenue may be overstated, or "
                      "a large share of takings is not flowing through this account (cash, or another bank). "
                      "Lenders treat this as the statements contradicting the financials.")
            fix = "Bank all revenue through the business account so deposits corroborate the income statement."
        elif gap > 0.25:
            direction = "deposits_above_revenue"
            interp = ("Banked deposits materially exceed declared revenue — there may be undisclosed income, "
                      "owner top-ups, or personal funds mixed into the business account.")
            fix = "Separate personal funds from the business account and reconcile deposits to declared revenue."
        else:
            direction = "aligned"
            interp = "Banked deposits reconcile reasonably with declared revenue."
            fix = ""
        reconciliation = {"available": True,
                          "declared_revenue": round(declared_revenue, 2),
                          "annualized_deposits": annualized_deposits,
                          "gap_pct": round(gap * 100, 1),
                          "material": material, "direction": direction,
                          "interpretation": interp}
        if material:
            risk_points += 2
            reasons.append(("high", "Bank deposits don't reconcile with declared revenue (%.0f%% gap)."
                            % (gap * 100), fix))

    # ── 2. Cash-flow conduct metrics (lender's actual checklist) ──────────────
    avg_balance = _num(bank.get("avg_balance"))
    consistency = bank.get("deposit_consistency")  # set by bank_signals when monthly data exists
    bounced = bank.get("returned_debit_orders") or 0
    neg_rows = bank.get("negative_balance_rows") or 0
    overdraft = bank.get("overdraft_signals") or 0
    min_balance = _num(bank.get("min_balance"))
    net_flow = _num(bank.get("net_flow"))

    metrics = {
        "available": bank_ok,
        "period_months": period_months,
        "average_daily_balance": avg_balance,
        "average_monthly_deposits": avg_monthly_deposits,
        "deposit_consistency": consistency,
        "returned_debit_orders": bounced,
        "negative_balance_rows": neg_rows,
        "overdraft_signals": overdraft,
        "min_balance": min_balance,
        "net_flow": net_flow,
    }
    if bank_ok:
        if bounced:
            risk_points += min(4, 2 * bounced)
            reasons.append(("high", "%d returned/bounced debit order(s) — the single biggest red flag for a lender." % bounced,
                            "Ensure the account is funded ahead of debit-order dates; clear any arrears."))
        if neg_rows or overdraft:
            risk_points += 2
            reasons.append(("high", "Account goes negative / uses overdraft — signals thin liquidity.",
                            "Build a buffer so the account stays positive across the month."))
        if net_flow is not None and net_flow < 0:
            risk_points += 2
            reasons.append(("medium", "Net cash outflow over the statement period.",
                            "Show a few months of positive net cash flow before applying."))
        if period_months and period_months < 3:
            risk_points += 1
            reasons.append(("medium", "Fewer than 3 months of statements — lenders want 3–6 months of history.",
                            "Gather at least 3–6 months of business bank statements."))
        if consistency in ("variable", "erratic"):
            risk_points += 1
            reasons.append(("medium", "Deposits are %s month-to-month — lumpy income reads as higher risk." % consistency,
                            "Smooth income where possible (retainers, deposits) and explain seasonality."))
    else:
        reasons.append(("medium", "No usable bank statement — lenders weight bank conduct heavily; without it an application stalls.",
                        "Upload 3–6 months of business bank statements."))

    # ── 3. Indicative borrowing capacity ─────────────────────────────────────
    borrowing = {"working_capital_facility": None, "term_loan": None,
                 "assumptions": "Indicative only. Term loan assumes ~%.0f%% p.a. over %d years; "
                                "DSCR %.2f (prudent) to %.2f (generous). Lenders vary widely."
                                % (_TERM_RATE * 100, _TERM_YEARS, _DSCR_PRUDENT, _DSCR_GENEROUS)}
    if avg_monthly_deposits and deposits_reliable:
        borrowing["working_capital_facility"] = {
            "low": round(0.8 * avg_monthly_deposits, 2),
            "high": round(1.5 * avg_monthly_deposits, 2),
            "basis": "0.8x–1.5x average monthly deposits (revenue-based / short-term facility)."}
    adj_low = _num(normalization.get("adjusted_ebitda_low"))
    if adj_low and adj_low > 0:
        service_prudent = adj_low / _DSCR_PRUDENT
        service_generous = adj_low / _DSCR_GENEROUS
        borrowing["term_loan"] = {
            "supportable_annual_debt_service_low": round(service_prudent, 2),
            "supportable_annual_debt_service_high": round(service_generous, 2),
            "implied_principal_low": _annuity_principal(service_prudent),
            "implied_principal_high": _annuity_principal(service_generous),
            "basis": "Adjusted EBITDA ÷ DSCR, converted to a term-loan principal."}
    elif adj_low is not None and adj_low <= 0:
        risk_points += 2
        reasons.append(("high", "Adjusted (normalised) EBITDA is not positive — limited capacity to service new debt.",
                        "Improve operating profit / confirm legitimate add-backs before borrowing."))

    # ── 4. SA structural flag carried through from normalization ─────────────
    loan_flag = normalization.get("loan_account_flag") or {}
    if loan_flag.get("flagged"):
        risk_points += 2 if loan_flag.get("level") == "high" else 1
        reasons.append(("high" if loan_flag.get("level") == "high" else "medium",
                        "Owner draws a loan account rather than a salary — no payslip trail for affordability scoring.",
                        loan_flag.get("fix", "Pay a regular PAYE salary so there is a payslip record.")))

    # ── 5. Decline-risk verdict ───────────────────────────────────────────────
    level = "high" if risk_points >= 5 else "medium" if risk_points >= 2 else "low"
    verdict = {
        "low": "A typical lender would likely progress this application on cash-flow grounds.",
        "medium": "A lender would hesitate — fixable issues are holding this application back.",
        "high": "A lender would most likely decline on cash-flow grounds today.",
    }[level]
    ranked = sorted(reasons, key=lambda r: {"high": 0, "medium": 1, "low": 2}[r[0]])

    return {
        "available": True,
        "decline_risk": level,
        "verdict": verdict,
        "reasons": [{"severity": s, "issue": t, "fix": f} for (s, t, f) in ranked],
        "reconciliation": reconciliation,
        "cash_flow_metrics": metrics,
        "borrowing_capacity": borrowing,
        "note": ("Indicative lender's-eye view from your own bank statements + financials (deterministic, "
                 "no AI in the numbers). Decision-support to help you get application-ready — NOT a credit "
                 "decision and NOT part of the Imara Score."),
    }
