"""
derived_metrics.py - deterministic metrics the specialist agents used to compute
by eye in the prompt. Arithmetic belongs in code: these functions calculate the
numbers exactly from memory.financial_figures and hand the agent a block to
NARRATE, with the inputs and assumptions stated so nothing is invented.

Every block returns "" when the needed figures are absent, so an agent simply
doesn't receive it (and is not tempted to fabricate). Nothing here changes the
Imara Score - it only grounds the agents' narrative findings.
"""
import math
from services.sa_rates import PRIME_RATE, SME_DEBT_MARGIN_LOW, SME_DEBT_MARGIN_HIGH, STRESS_BPS
from services.benchmark_service import get_benchmarks

_DSCR_TERM_YEARS = 5
_INV_HOLDING_COST = 0.30          # 30% of inventory value p.a. (storage/insurance/obsolescence/opportunity)
_TARGET_CREDITOR_DAYS = 60.0
_TARGET_DSCR = 1.25


def _fnum(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    try:
        x = float(str(v).strip().replace(" ", "").replace(",", "").replace("R", "").replace("ZAR", "").strip("()"))
        return x if math.isfinite(x) else None
    except (ValueError, TypeError):
        return None


def _figs(memory):
    raw = getattr(memory, "financial_figures", {}) or {}
    if not isinstance(raw, dict):
        return {}
    out = {}
    for k, v in raw.items():
        n = _fnum(v)
        if n is not None:
            out[k] = n
    rev = _fnum(getattr(memory, "annual_revenue", 0))
    if rev and "revenue" not in out:
        out["revenue"] = rev
    return out


def _r(x):
    return "R{:,.0f}".format(x)


def annual_debt_service(principal, annual_rate, years=_DSCR_TERM_YEARS):
    """Level annuity payment (interest + principal) on `principal` at `annual_rate` over `years`."""
    if principal <= 0:
        return 0.0
    if annual_rate <= 0:
        return principal / years
    return principal * annual_rate / (1 - (1 + annual_rate) ** (-years))


# ───────────────────────── EBITDA bridge (FinancialAgent) ─────────────────────────
def ebitda_bridge_block(memory):
    f = _figs(memory)
    rev = f.get("revenue")
    op = f.get("operating_profit")
    if not rev or op is None:
        return ""
    m = (get_benchmarks(getattr(memory, "industry_key", "general") or "general") or {}).get("margins", {})
    op_bench = m.get("operating_margin", 0.08)
    gm_bench = m.get("gross_margin", 0.30)

    ebit_margin = op / rev
    gap_pp = (op_bench - ebit_margin) * 100
    lines = ["PRE-COMPUTED EBITDA BRIDGE (exact; EBIT used as the EBITDA proxy because "
             "depreciation/amortisation is not separately available - narrate these, do not recompute):"]
    lines.append("- EBIT margin: {:.1f}% vs sector operating-margin benchmark {:.1f}% (gap {:.1f}pp)".format(
        ebit_margin * 100, op_bench * 100, gap_pp))
    if gap_pp > 0:
        lines.append("- Closing the margin gap is worth ~{} per year ({:.1f}pp x {})".format(
            _r(gap_pp / 100 * rev), gap_pp, _r(rev)))

    gp = f.get("gross_profit")
    if gp is None and "cogs" in f:
        gp = rev - f["cogs"]
    if gp is not None:
        gm = gp / rev
        gm_gap = (gm_bench - gm)
        if gm_gap > 0:
            lines.append("- Gross-margin drag: {:.1f}% vs {:.1f}% benchmark = ~{}/yr".format(
                gm * 100, gm_bench * 100, _r(gm_gap * rev)))
        opex = gp - op
        opex_ratio = opex / rev
        implied_opex_bench = max(0.0, gm_bench - op_bench)
        opex_excess = opex_ratio - implied_opex_bench
        if opex_excess > 0:
            lines.append("- Overhead drag: opex {:.1f}% of revenue vs implied benchmark {:.1f}% = ~{}/yr excess".format(
                opex_ratio * 100, implied_opex_bench * 100, _r(opex_excess * rev)))
    return "\n".join(lines)


# ───────────────────────── DSCR (CreditReadinessAgent) ─────────────────────────
def dscr_block(memory):
    f = _figs(memory)
    op = f.get("operating_profit")
    debt = f.get("total_debt")
    if op is None or not debt or debt <= 0:
        return ""
    rate = (PRIME_RATE + (SME_DEBT_MARGIN_LOW + SME_DEBT_MARGIN_HIGH) / 2) / 100.0   # prime + 4%
    ds = annual_debt_service(debt, rate)
    dscr = op / ds if ds else None
    stress_rate = rate + STRESS_BPS / 10000.0
    ds_s = annual_debt_service(debt, stress_rate)
    dscr_s = op / ds_s if ds_s else None
    lines = ["PRE-COMPUTED DEBT-SERVICE COVERAGE (exact; narrate these, do not recompute. EBIT used as the "
             "cash-flow proxy; debt service = level annuity on total debt {} over {}y at prime+4% = {:.1f}%):".format(
                 _r(debt), _DSCR_TERM_YEARS, rate * 100)]
    lines.append("- Estimated annual debt service: {}".format(_r(ds)))
    if dscr is not None:
        verdict = "below" if dscr < _TARGET_DSCR else "at/above"
        lines.append("- Estimated DSCR: {:.2f}x ({} the {:.2f}x lender target)".format(dscr, verdict, _TARGET_DSCR))
    if dscr_s is not None:
        lines.append("- Stressed DSCR at +{}bps ({:.1f}%): {:.2f}x".format(STRESS_BPS, stress_rate * 100, dscr_s))
    if f.get("interest"):
        lines.append("- Interest cover (EBIT / interest): {:.2f}x".format(op / f["interest"]))
    lines.append("- NOTE: DSCR is an estimate (real term/amortisation unknown); present it as indicative.")
    return "\n".join(lines)


# ───────────────────────── Procurement working capital (ProcurementAgent) ─────────────────────────
def procurement_wc_block(memory):
    f = _figs(memory)
    rev = f.get("revenue")
    cogs = f.get("cogs")
    payables = f.get("payables")
    inventory = f.get("inventory")
    base = cogs or rev
    lines = []
    if payables and base:
        cd = payables / base * 365
        if cd < _TARGET_CREDITOR_DAYS:
            freed = base * (_TARGET_CREDITOR_DAYS - cd) / 365
            lines.append("- Creditor terms: currently ~{:.0f} days; extending to {:.0f} days frees ~{} of working capital".format(
                cd, _TARGET_CREDITOR_DAYS, _r(freed)))
        else:
            lines.append("- Creditor terms: already ~{:.0f} days (at/above {:.0f}) - limited further upside".format(
                cd, _TARGET_CREDITOR_DAYS))
    if inventory and cogs:
        inv_days = inventory / cogs * 365
        holding = inventory * _INV_HOLDING_COST
        bench = (get_benchmarks(getattr(memory, "industry_key", "general") or "general") or {}).get(
            "efficiency", {}).get("inventory_turnover_days", 45)
        lines.append("- Inventory holding cost: ~{}/yr ({:.0f}% of {} stock)".format(
            _r(holding), _INV_HOLDING_COST * 100, _r(inventory)))
        if inv_days > bench:
            freed_i = cogs * (inv_days - bench) / 365
            lines.append("- Inventory days ~{:.0f} vs {:.0f} benchmark: cutting to benchmark frees ~{}".format(
                inv_days, bench, _r(freed_i)))
    if not lines:
        return ""
    return "PRE-COMPUTED WORKING-CAPITAL LEVERS (exact; narrate these, do not recompute):\n" + "\n".join(lines)


# ───────────────────────── Public Interest Score (SALegalAgent) ─────────────────────────
def pis_block(memory):
    rev = _fnum(getattr(memory, "annual_revenue", 0)) or _figs(memory).get("revenue")
    headcount = _fnum(getattr(memory, "headcount", 0)) or 0
    if not rev:
        return ""
    rev_pts = round(rev / 1_000_000)
    known = int(headcount) + int(rev_pts)
    min_pis = known + 1   # at least one shareholder; debt-holders + further shareholders add to this
    if min_pis >= 350:
        req = "PIS >= 350 -> AUDITED annual financial statements are required (Companies Act / Reg 28)."
    elif min_pis >= 100:
        req = ("PIS in the 100-349 band -> an INDEPENDENT REVIEW is required unless the company is "
               "owner-managed and every shareholder is also a director (then it may be exempt).")
    else:
        req = "PIS < 100 -> no statutory audit or independent review is mandated (a compilation suffices), absent other triggers."
    return ("PRE-COMPUTED PUBLIC INTEREST SCORE (exact, from headcount + revenue/R1m; narrate this, do not recompute):\n"
            "- PIS (minimum) = headcount {} + revenue points {} + >=1 shareholder = >= {}\n"
            "- {}\n"
            "- NOTE: add the actual number of debt-holders and shareholders to refine the PIS; this is the floor.".format(
                int(headcount), int(rev_pts), min_pis, req))
