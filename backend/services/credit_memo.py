"""
Lender's credit memo — the 5 Cs of credit + an explicit DSCR, in the bank's own
language. DETERMINISTIC; composes data Imara already computes (financial_figures,
financial_ratios, normalization, lender_view, bank_signals, credit grade, SA tax,
macro) — it does NOT recompute or duplicate them.

Research basis (SA SME lending): a credit committee reads a file through the
5 Cs — Character, Capacity, Capital, Collateral, Conditions — and the hard
number is the Debt-Service Coverage Ratio (DSCR), with lenders wanting ~1.15-1.25x+.
SA lending is collateral-led, and most SMEs are declined on cash flow / presentation
rather than viability. This memo surfaces exactly which C's pass or fail so the SME
can fix the file BEFORE it reaches a lender.

Decision-support only — NOT a credit decision and NOT an Imara Score input.
"""

DSCR_TARGET = 1.25     # lenders typically want >= ~1.15-1.25x
DSCR_FLOOR = 1.00


def _n(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        return f if f == f and f not in (float("inf"), float("-inf")) else None
    try:
        s = str(v).strip().replace(" ", "").replace(",", "").replace("R", "").replace("ZAR", "")
        neg = s.startswith("(") and s.endswith(")")
        f = float(s.strip("()"))
        return -f if neg else f
    except (ValueError, TypeError):
        return None


def _ratio_val(ratios, key):
    r = (ratios or {}).get(key)
    return _n(r.get("value")) if isinstance(r, dict) else None


def _dscr(figs, norm):
    """Explicit DSCR. EBITDA / annual debt service (interest + ~1/5 of debt principal)."""
    ebitda = _n((norm or {}).get("adjusted_ebitda_low"))
    if ebitda is None:
        ebitda = _n(figs.get("ebitda")) or _n(figs.get("operating_profit"))
    interest = _n(figs.get("interest")) or 0.0
    debt = _n(figs.get("total_debt"))
    principal_est = (debt / 5.0) if (debt and debt > 0) else 0.0
    service = interest + principal_est

    if ebitda is None:
        return {"value": None, "target": DSCR_TARGET, "status": "unknown",
                "basis": "Needs operating profit / EBITDA to assess debt-service capacity."}
    if service <= 0:
        return {"value": None, "target": DSCR_TARGET,
                "status": "pass" if ebitda > 0 else "fail",
                "basis": ("No material existing debt service detected — capacity assessed on positive "
                          "earnings; new debt would be serviced from this EBITDA."
                          if ebitda > 0 else "Earnings are not positive — limited capacity to service debt.")}
    dscr = ebitda / service
    status = "pass" if dscr >= DSCR_TARGET else "watch" if dscr >= DSCR_FLOOR else "fail"
    return {"value": round(dscr, 2), "target": DSCR_TARGET, "status": status,
            "basis": ("EBITDA R{:,.0f} / annual debt service R{:,.0f} (interest + ~1/5 of debt principal). "
                      "Lenders want >= ~{}x.".format(ebitda, service, DSCR_TARGET))}


def build_credit_memo(report) -> dict:
    """Return the 5-Cs grid + DSCR. Pure; never raises."""
    if not isinstance(report, dict):
        return {"available": False, "reason": "No report."}
    figs = report.get("financial_figures") or {}
    ratios = report.get("financial_ratios") or {}
    norm = report.get("normalization") or {}
    bank = report.get("bank_signals") or {}
    lv = report.get("lender_view") or {}
    grade = (report.get("credit_grade") or "").strip().upper()

    if not figs and not bank.get("available"):
        return {"available": False,
                "reason": "Needs financials and/or a bank statement to build a credit memo."}

    dscr = _dscr(figs, norm)
    cs = []

    # 1. CHARACTER — conduct & compliance
    bounced = bank.get("returned_debit_orders") or 0
    neg = bank.get("negative_balance_rows") or 0
    tax_clear = report.get("sa_tax_clearance_status")
    vat = report.get("sa_vat_status")
    if bounced:
        cs.append(("Character", "fail",
                   "{} returned/bounced debit order(s) — the single biggest conduct red flag.".format(bounced),
                   "Fund the account ahead of debit-order dates and show a clean recent history."))
    elif neg or (tax_clear == "expired") or (vat == "risk"):
        cs.append(("Character", "watch",
                   "Account dips negative or SARS status needs attention — lenders read both as conduct risk.",
                   "Keep the account positive; get a valid tax clearance and VAT compliance."))
    else:
        cs.append(("Character", "pass",
                   "No bounced debit orders or adverse SARS/VAT flags detected." +
                   (" Credit grade {}.".format(grade) if grade else ""),
                   ""))

    # 2. CAPACITY — DSCR (the headline number)
    cap_status = {"pass": "pass", "watch": "watch", "fail": "fail", "unknown": "unknown"}[dscr["status"]]
    cap_ev = ("DSCR {}x vs ~{}x target. ".format(dscr["value"], dscr["target"]) if dscr["value"] is not None
              else "") + dscr["basis"]
    cs.append(("Capacity", cap_status, cap_ev,
               "" if cap_status == "pass" else
               "Lift operating profit or reduce debt service so DSCR clears ~{}x.".format(DSCR_TARGET)))

    # 3. CAPITAL — owner's stake / gearing
    equity = _n(figs.get("equity"))
    de = _ratio_val(ratios, "debt_to_equity")
    if equity is not None and equity < 0:
        cs.append(("Capital", "fail", "Negative equity — the business owes more than it owns.",
                   "Inject capital or retain earnings to rebuild equity before borrowing."))
    elif de is not None and de > 3:
        cs.append(("Capital", "fail", "Very high gearing (debt-to-equity {}x).".format(round(de, 1)),
                   "Reduce debt or add equity — lenders resist lending into an over-geared balance sheet."))
    elif de is not None and de > 1.5:
        cs.append(("Capital", "watch", "Elevated gearing (debt-to-equity {}x).".format(round(de, 1)),
                   "Bring gearing toward <=1.5x to strengthen the application."))
    elif de is not None:
        cs.append(("Capital", "pass", "Healthy gearing (debt-to-equity {}x).".format(round(de, 1)), ""))
    elif equity is not None and equity > 0:
        cs.append(("Capital", "pass", "Positive owner's equity.", ""))
    else:
        cs.append(("Capital", "unknown", "No balance sheet — can't assess equity/gearing.",
                   "Provide a balance sheet so capital structure can be assessed."))

    # 4. COLLATERAL — pledgeable assets / security position
    ta = _n(figs.get("total_assets"))
    ca = _n(figs.get("current_assets"))
    fixed = (ta - ca) if (ta is not None and ca is not None) else None
    inv = _n(figs.get("inventory")) or 0.0
    rec = _n(figs.get("receivables")) or 0.0
    security = (fixed or 0.0) + inv + rec
    if security > 0:
        status = "pass" if security >= 250_000 else "watch"
        cs.append(("Collateral", status,
                   "~R{:,.0f} in fixed + working-capital assets potentially available as security "
                   "(fixed R{:,.0f}, inventory R{:,.0f}, receivables R{:,.0f}).".format(
                       security, fixed or 0.0, inv, rec),
                   "" if status == "pass" else
                   "Thin security — expect a cash-flow-based (harder) assessment in SA's collateral-led market."))
    else:
        cs.append(("Collateral", "watch",
                   "Limited tangible assets to pledge — expect an unsecured / cash-flow-based assessment, "
                   "which is harder in SA's collateral-led lending market.",
                   "Identify pledgeable assets (equipment, property, a notarial bond over movables) or a surety."))

    # 5. CONDITIONS — macro / sector context (soft)
    macro = report.get("macro_overall_exposure")
    if macro == "high":
        driver = report.get("macro_top_driver") or "the macro environment"
        cs.append(("Conditions", "watch",
                   "High macro exposure ({}) — lenders price in the operating environment.".format(driver),
                   "Show resilience to the key driver (hedging, pricing power, energy backup)."))
    else:
        cs.append(("Conditions", "note",
                   "Macro/sector context " + (("exposure: " + macro) if macro else "not flagged as high") +
                   ". Lenders also weight industry outlook and the specific use of funds.",
                   ""))

    five_cs = [{"c": c, "status": s, "evidence": e, "fix": f} for (c, s, e, f) in cs]
    fails = sum(1 for x in five_cs if x["status"] == "fail")
    watches = sum(1 for x in five_cs if x["status"] == "watch")
    decline = lv.get("decline_risk")
    if fails >= 1 or decline == "high":
        committee = "A credit committee would most likely DECLINE this file today — fix the failing C's first."
    elif watches >= 2 or decline == "medium":
        committee = "A credit committee would HESITATE — fixable C's are holding the file back."
    else:
        committee = "A credit committee would likely PROGRESS this file on the evidence presented."

    return {
        "available": True,
        "dscr": dscr,
        "five_cs": five_cs,
        "fails": fails,
        "watches": watches,
        "committee_read": committee,
        "note": ("How a SA lender's credit committee would read your file (the 5 Cs + DSCR), computed "
                 "from your own figures — deterministic, no AI in the numbers. Decision-support to get "
                 "application-ready; NOT a credit decision and NOT part of the Imara Score."),
    }
