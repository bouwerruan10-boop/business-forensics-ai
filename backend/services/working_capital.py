"""
Working-capital cycle + cash-trapped-in-stock release — DETERMINISTIC.

A supply-chain / CFO's headline deliverable is "you have R X trapped in working
capital above sector norms; release it." Imara already computes the individual
days (inventory_days, debtor_days, creditor_days, each vs a sector benchmark) in
financial_ratios — this module COMPOSES them (does not recompute) into:
  - the Cash Conversion Cycle (CCC = inventory days + debtor days - creditor days),
    actual vs the sector-benchmark CCC; and
  - the cash that reaching benchmark inventory/debtor days would FREE — the
    working-capital a facility would otherwise provide, without the debt.

Decision-support; not an Imara Score input. No AI in the numbers.
"""


def _n(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if v == v and v not in (float("inf"), float("-inf")) else None
    try:
        s = str(v).strip().replace(" ", "").replace(",", "").replace("R", "").replace("ZAR", "")
        f = float(s.strip("()"))
        return f
    except (ValueError, TypeError):
        return None


def _rv(ratios, key):
    r = (ratios or {}).get(key)
    if isinstance(r, dict):
        return _n(r.get("value")), _n(r.get("benchmark"))
    return None, None


def build_working_capital(report) -> dict:
    """Compose the CCC + cash-release opportunity from already-computed ratios. Pure."""
    if not isinstance(report, dict):
        return {"available": False, "reason": "No report."}
    ratios = report.get("financial_ratios") or {}
    figs = report.get("financial_figures") or {}
    inv_d, inv_b = _rv(ratios, "inventory_days")
    deb_d, deb_b = _rv(ratios, "debtor_days")
    cre_d, cre_b = _rv(ratios, "creditor_days")
    cogs = _n(figs.get("cogs"))
    rev = _n(figs.get("revenue"))

    if inv_d is None and deb_d is None:
        return {"available": False,
                "reason": "Needs inventory and/or receivables plus revenue/COGS to assess the working-capital cycle."}

    # Cash Conversion Cycle (use 0 for any missing leg, and say which legs were available).
    legs = []
    if inv_d is not None:
        legs.append("inventory")
    if deb_d is not None:
        legs.append("receivables")
    if cre_d is not None:
        legs.append("payables")
    ccc = (inv_d or 0) + (deb_d or 0) - (cre_d or 0)
    ccc_bench = ((inv_b or 0) + (deb_b or 0) - (cre_b or 0)) if (inv_b or deb_b or cre_b) else None
    if ccc_bench is not None:
        ccc_status = "good" if ccc <= ccc_bench else "warning" if ccc <= ccc_bench * 1.4 else "critical"
    else:
        ccc_status = "unknown"

    # Cash trapped above sector norms = the release opportunity.
    items = []
    total_release = 0.0
    if inv_d is not None and inv_b and cogs and cogs > 0 and inv_d > inv_b:
        amt = (inv_d - inv_b) / 365.0 * cogs
        total_release += amt
        items.append({"driver": "Inventory", "excess_days": round(inv_d - inv_b, 1),
                      "amount": round(amt, 2),
                      "fix": "Cut slow/dead stock and tighten reorder points to reach ~{:.0f} inventory days.".format(inv_b)})
    if deb_d is not None and deb_b and rev and rev > 0 and deb_d > deb_b:
        amt = (deb_d - deb_b) / 365.0 * rev
        total_release += amt
        items.append({"driver": "Receivables", "excess_days": round(deb_d - deb_b, 1),
                      "amount": round(amt, 2),
                      "fix": "Tighten collections / deposit terms to reach ~{:.0f} debtor days.".format(deb_b)})

    release = {
        "total": round(total_release, 2),
        "items": items,
        "basis": ("Cash that reaching sector-benchmark inventory/debtor days would free up — the working "
                  "capital a facility would otherwise provide, without taking on debt."),
    } if items else {
        "total": 0.0, "items": [],
        "basis": "Inventory and debtor days are at or below sector norms — no obvious trapped cash to release.",
    }

    return {
        "available": True,
        "cash_conversion_cycle": {
            "value": round(ccc, 1),
            "benchmark": round(ccc_bench, 1) if ccc_bench is not None else None,
            "status": ccc_status,
            "legs_available": legs,
            "components": {
                "inventory_days": round(inv_d, 1) if inv_d is not None else None,
                "debtor_days": round(deb_d, 1) if deb_d is not None else None,
                "creditor_days": round(cre_d, 1) if cre_d is not None else None,
            },
            "interpretation": ("Days from paying for stock to collecting cash. Lower is better — it means less "
                               "cash tied up in the operating cycle."),
        },
        "working_capital_release": release,
        "note": ("Working-capital cycle + the cash trapped above sector norms, composed from your computed "
                 "ratios (deterministic, no AI in the numbers). Decision-support to free up cash internally "
                 "before borrowing it; not an Imara Score input."),
    }
