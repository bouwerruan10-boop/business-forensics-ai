"""
Funding-Fit / Which-Path recommender — deterministic, FAIS-safe.

Research (2026-06): SA already has loan marketplaces (match offers), alt-lenders
(answer only "can you get OUR product"), and funding-readiness tools (subjective
self-assessment questionnaires). NONE map a firm — from its ACTUAL computed
financials + bank conduct — to the funding ARCHETYPE that fits, with the reasons
and what's still needed. This module does that as the natural companion to the
Bank-Ready Pack: where you stand -> why -> what to fix -> which path fits.

Objective information about funding TYPES only — NOT a recommendation that any
particular product/provider is suitable for you (FAIS s1(3)(a) framing). Not a
credit decision; not an Imara Score input. Deterministic; no AI in the logic.
"""
import math

__all__ = ["recommend_funding"]

# Standardised SA commercial-lender eligibility floors (from the market scan).
_TURNOVER_FLOOR = 1_000_000      # > R1m annual turnover
_TRADING_FLOOR_MONTHS = 12       # >= 12 months trading
_CARD_SECTORS = {"retail", "hospitality", "restaurant", "wholesale", "services", "ecommerce"}


def _num(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    s = str(v).strip().replace(" ", "").replace(",", "").replace("R", "").replace("ZAR", "")
    try:
        f = float(s)
        return f if math.isfinite(f) else None
    except ValueError:
        return None


def _trading_months(report):
    y = _num(report.get("years_in_business"))
    if y is not None:
        return y * 12 if y < 100 else y     # treat small numbers as years, large as months
    return None


def _opt(label, fit, why, requirements, caveat, key):
    return {"archetype": key, "label": label, "fit": fit, "why": why,
            "requirements": requirements, "caveat": caveat}


def recommend_funding(report: dict) -> dict:
    report = report or {}
    g = report.get
    figs = g("financial_figures") if isinstance(g("financial_figures"), dict) else {}
    bank = g("bank_signals") if isinstance(g("bank_signals"), dict) else {}
    lv = g("lender_view") if isinstance(g("lender_view"), dict) else {}
    norm = g("normalization") if isinstance(g("normalization"), dict) else {}
    sb = g("supplier_benchmark") if isinstance(g("supplier_benchmark"), dict) else {}
    g("financial_ratios") if isinstance(g("financial_ratios"), dict) else {}

    revenue = _num(figs.get("revenue")) or _num(g("annual_revenue")) or 0.0
    months = _trading_months(report)
    cipc = bool(g("cipc_number")) or ("pty" in str(g("entity_type") or "").lower())
    industry = str(g("industry_key") or g("industry") or "").lower()

    # ── eligibility floors ────────────────────────────────────────────────
    turnover_ok = revenue >= _TURNOVER_FLOOR
    floor_met = turnover_ok and (months is not None and months >= _TRADING_FLOOR_MONTHS) and cipc
    elig = {
        "turnover_ok": turnover_ok, "trading_ok": bool(months is not None and months >= _TRADING_FLOOR_MONTHS),
        "cipc_ok": cipc, "floor_met": floor_met,
        "notes": [
            "Annual turnover %s the ~R1m commercial floor." % ("meets" if turnover_ok else "is below"),
            ("Trading history %s the ~12-month floor." % ("meets" if (months and months >= 12) else "is below/unknown")),
            ("Registered with CIPC." if cipc else "CIPC registration not evidenced — most commercial lenders require it."),
        ],
    }

    # ── cash-flow conduct signals ─────────────────────────────────────────
    bounced = bank.get("returned_debit_orders") or 0
    decline = lv.get("decline_risk")
    adj_low = _num(norm.get("adjusted_ebitda_low"))
    receivables = _num(figs.get("receivables")) or 0.0
    rec_ratio = (receivables / revenue) if revenue else 0.0
    card_accepting = (industry in _CARD_SECTORS) or any(
        (o or {}).get("category") == "card_machine_fees" for o in (sb.get("opportunities") or []) if isinstance(o, dict))

    opts = []

    # 1) Revenue-based / turnover advance
    if card_accepting and revenue >= 1_000_000 and (months is None or months >= 6):
        fit = "good"
    elif revenue >= 500_000 and (months is None or months >= 6):
        fit = "possible"
    else:
        fit = "unlikely"
    opts.append(_opt("Revenue-based / turnover advance", fit,
                     "Repaid as a fixed share of card/turnover, so it flexes with sales — fast and unsecured." +
                     ("" if card_accepting else " (Best fit when a large share of sales runs through a card machine.)"),
                     "~6+ months of card/turnover history; a card-accepting or steady-revenue business.",
                     "Effective cost is typically higher than a bank loan; best for short-term/seasonal needs.",
                     "revenue_based_advance"))

    # 2) Unsecured working-capital facility / short-term business loan
    if floor_met and decline in ("low", "medium") and not bounced:
        fit = "good"
    elif floor_met:
        fit = "possible"
    else:
        fit = "unlikely"
    opts.append(_opt("Unsecured working-capital facility", fit,
                     "Fast, unsecured short-term capital (often 6–12 months), with decisions in hours from cash-flow data.",
                     "≥12 months trading, >R1m turnover, CIPC registered, and clean recent bank conduct (no bounced debit orders).",
                     "Short term and unsecured — rates are higher than a secured bank term loan.",
                     "working_capital_facility"))

    # 3) Invoice discounting / debtor finance
    if rec_ratio >= 0.12 and revenue >= 1_000_000:
        fit = "good"
    elif receivables > 0:
        fit = "possible"
    else:
        fit = "unlikely"
    opts.append(_opt("Invoice discounting / debtor finance", fit,
                     "Unlocks cash tied up in unpaid invoices; the facility scales with your receivables book.",
                     "Invoices to creditworthy (ideally larger) customers; a B2B model with real debtors.",
                     "Cost is charged per invoice/period; depends on the quality of your debtors.",
                     "invoice_discounting"))

    # 4) Bank term loan
    if floor_met and decline == "low" and (adj_low or 0) > 0:
        fit = "good"
    elif floor_met and decline == "medium" and (adj_low or 0) > 0:
        fit = "possible"
    else:
        fit = "unlikely"
    opts.append(_opt("Bank term loan", fit,
                     "Larger, longer and cheaper than alt-lender capital — suited to growth or capex once the profile is strong.",
                     "Signed/AFS financials, demonstrated affordability (debt-service cover), often security/collateral.",
                     "Slow and documentation-heavy; banks still underwrite term loans manually.",
                     "bank_term_loan"))

    # 5) Asset / equipment finance (informational — depends on a capex need)
    opts.append(_opt("Asset / equipment finance", "possible",
                     "If the need is to buy equipment or vehicles, the asset itself secures the finance.",
                     "A specific asset to finance; the asset acts as security, easing approval.",
                     "Tied to the asset; not a source of general working capital.",
                     "asset_equipment_finance"))

    # 6) Development / government funding
    if not floor_met:
        fit = "good"      # thin-file / early-stage often best served here
    else:
        fit = "possible"
    opts.append(_opt("Development / government funding (e.g. SEFA, IDC, NEF)", fit,
                     "Development-finance institutions apply developmental criteria (jobs, B-BBEE, priority sectors) and can be more patient and cheaper.",
                     "A business plan and demonstrable developmental impact; sector/ownership fit.",
                     "Slow and eligibility-specific; not fast working capital.",
                     "development_funding"))

    order = {"good": 0, "possible": 1, "unlikely": 2}
    opts.sort(key=lambda o: order.get(o["fit"], 3))
    primary = [o["label"] for o in opts if o["fit"] == "good"]

    # ── fix-first gate ────────────────────────────────────────────────────
    gate_reasons = []
    if not turnover_ok:
        gate_reasons.append("Turnover is below the ~R1m commercial floor.")
    if months is not None and months < 12:
        gate_reasons.append("Trading history is under 12 months.")
    if not cipc:
        gate_reasons.append("No evidence of CIPC registration.")
    if bounced:
        gate_reasons.append("%d returned/bounced debit order(s) — the single biggest red flag for a lender." % bounced)
    if decline == "high":
        gate_reasons.append("Cash-flow decline-risk is currently high.")
    gate = ({"status": "strengthen-first", "reasons": gate_reasons,
             "pointer": "Address these first (see the Bank-Ready Pack), then the commercial paths open up."}
            if gate_reasons else {"status": "application-ready"})

    return {
        "available": True,
        "eligibility": elig,
        "gate": gate,
        "primary_paths": primary,
        "options": opts,
        "note": ("Objective information about funding TYPES that commonly fit a profile like this — NOT a "
                 "recommendation that any particular product or provider is suitable for you, and not a credit "
                 "decision. Deterministic, from your own computed figures and bank conduct."),
    }
