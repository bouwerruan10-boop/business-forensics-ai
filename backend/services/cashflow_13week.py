"""
cashflow_13week.py - deterministic 13-week direct-method cash-flow projection.

This is the LIQUIDITY horizon that complements the ForecastAgent's 12-month
strategic scenarios. The 13-week direct-method forecast is the SME survival tool:
it answers "when does cash get tight / run out", which the annual P&L view hides.

Imara has annual figures, not a weekly cash ledger, so this is a transparent
model built from the run-rate plus the two lumpy cash events most SMEs feel -
loan instalments and net VAT remittances. Every assumption is returned in the
output and the agent is told to present it as indicative. All arithmetic; no LLM.
Nothing here changes the Imara Score.
"""
import math

from services.sa_rates import PRIME_RATE, SME_DEBT_MARGIN_LOW, SME_DEBT_MARGIN_HIGH
from services.derived_metrics import annual_debt_service, _fnum

WEEKS = 13
_DEBT_WEEKS = (4, 9, 13)          # ~month-ends inside a 13-week (≈3-month) window
_VAT_WEEK = 8                     # one bi-monthly VAT remittance lands in the window
_VAT_PAYMENTS_PER_YEAR = 6        # VAT201 is bi-monthly for most SMEs


def _g(figs, key):
    return _fnum((figs or {}).get(key))


def project_13week(figs, opening_cash=None, vat_registered=False, debt_service_annual=None):
    """Project 13 weeks of direct cash flow. Returns {available, weeks, summary...}."""
    figs = figs or {}
    rev = _g(figs, "revenue")
    op = _g(figs, "operating_profit")
    if not rev or rev <= 0 or op is None:
        return {"available": False, "reason": "needs revenue and operating profit"}

    gp = _g(figs, "gross_profit")
    if gp is None and _g(figs, "cogs") is not None:
        gp = rev - _g(figs, "cogs")

    # opening cash proxy: liquid current assets net of receivables + inventory
    ca, recv, inv = _g(figs, "current_assets"), _g(figs, "receivables"), _g(figs, "inventory")
    opening_known = opening_cash is not None
    if opening_cash is None:
        if ca is not None:
            opening_cash = max(0.0, ca - (recv or 0.0) - (inv or 0.0))
            opening_known = True
        else:
            opening_cash = 0.0

    # debt service lump (monthly = annual / 12)
    if debt_service_annual is None:
        debt = _g(figs, "total_debt")
        rate = (PRIME_RATE + (SME_DEBT_MARGIN_LOW + SME_DEBT_MARGIN_HIGH) / 2) / 100.0
        debt_service_annual = annual_debt_service(debt, rate) if (debt and debt > 0) else 0.0
    debt_lump = debt_service_annual / 12.0 if debt_service_annual else 0.0

    # net VAT remittance lump (≈ 15% of value-added, bi-monthly)
    vat_lump = 0.0
    if vat_registered and gp and gp > 0:
        vat_lump = 0.15 * gp / _VAT_PAYMENTS_PER_YEAR

    weekly_inflow = rev / 52.0
    weekly_base_outflow = (rev - op) / 52.0        # operating costs spread evenly; net run-rate = op/52

    weeks = []
    bal = opening_cash
    min_bal, min_week = None, None
    neg_week = None
    for w in range(1, WEEKS + 1):
        opening = bal
        lumps = []
        lump_total = 0.0
        if debt_lump and w in _DEBT_WEEKS:
            lumps.append({"label": "Loan instalment", "amount": round(debt_lump)})
            lump_total += debt_lump
        if vat_lump and w == _VAT_WEEK:
            lumps.append({"label": "VAT remittance", "amount": round(vat_lump)})
            lump_total += vat_lump
        outflow = weekly_base_outflow + lump_total
        net = weekly_inflow - outflow
        closing = opening + net
        bal = closing
        if min_bal is None or closing < min_bal:
            min_bal, min_week = closing, w
        if neg_week is None and closing < 0:
            neg_week = w
        weeks.append({
            "week": w,
            "opening": round(opening),
            "inflow": round(weekly_inflow),
            "outflow": round(outflow),
            "lumps": lumps,
            "net": round(net),
            "closing": round(closing),
        })

    assumptions = [
        "Collections and operating outflows spread evenly at the annual run-rate "
        "(revenue/52, costs/52); steady going concern.",
        "Loan instalments modelled monthly (weeks 4, 9, 13) as annual debt service / 12.",
        ("Net VAT remittance (~15%% of gross profit, bi-monthly) modelled in week %d."
         % _VAT_WEEK) if vat_lump else "No VAT remittance modelled (not VAT-registered or no gross profit).",
        ("Opening cash proxied as current assets - receivables - inventory = %s."
         % "{:,.0f}".format(opening_cash)) if opening_known
        else "Opening cash unknown (no balance sheet) - trajectory shown from zero; read the SHAPE, not the level.",
        "Indicative liquidity model from annual figures, not a transaction-level cash ledger.",
    ]
    return {
        "available": True,
        "weeks": weeks,
        "opening_cash": round(opening_cash),
        "opening_known": opening_known,
        "weekly_inflow": round(weekly_inflow),
        "weekly_base_outflow": round(weekly_base_outflow),
        "weekly_operating_net": round(weekly_inflow - weekly_base_outflow),
        "debt_service_monthly": round(debt_lump),
        "vat_remittance": round(vat_lump),
        "min_balance": round(min_bal),
        "min_week": min_week,
        "goes_negative": neg_week is not None,
        "negative_week": neg_week,
        "ending_cash": weeks[-1]["closing"],
        "assumptions": assumptions,
    }


def from_report(report, memory=None):
    figs = (report or {}).get("financial_figures") or {}
    vat = bool(getattr(memory, "vat_registered", False)) if memory is not None else False
    return project_13week(figs, vat_registered=vat)


def cashflow_summary_block(memory):
    """Compact text block for the ForecastAgent to narrate the liquidity horizon."""
    figs = getattr(memory, "financial_figures", {}) or {}
    res = project_13week(figs, vat_registered=bool(getattr(memory, "vat_registered", False)))
    if not res.get("available"):
        return ""
    lines = ["13-WEEK LIQUIDITY HORIZON (deterministic direct-method projection - narrate this as the "
             "SHORT-TERM cash view, distinct from the 12-month strategic scenarios; do not recompute):"]
    lines.append("- Opening cash (proxy): R{:,.0f} | weekly operating net: R{:,.0f}".format(
        res["opening_cash"], res["weekly_operating_net"]))
    if res["debt_service_monthly"]:
        lines.append("- Monthly loan instalment modelled: R{:,.0f}".format(res["debt_service_monthly"]))
    if res["vat_remittance"]:
        lines.append("- Bi-monthly VAT remittance modelled: R{:,.0f}".format(res["vat_remittance"]))
    lines.append("- Cash low point: R{:,.0f} in week {}".format(res["min_balance"], res["min_week"]))
    if res["goes_negative"]:
        lines.append("- CASH GOES NEGATIVE in week {} - flag this as the priority liquidity risk.".format(
            res["negative_week"]))
    else:
        lines.append("- Cash stays positive across all 13 weeks (ending R{:,.0f}).".format(res["ending_cash"]))
    return "\n".join(lines)
