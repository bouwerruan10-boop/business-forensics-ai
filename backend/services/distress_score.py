"""
Altman Z''-score (emerging-markets variant) — an INDEPENDENT, published, fully
deterministic financial-distress model, used by Imara as an EXTERNAL
convergent-validity anchor for the (heuristic) Imara Score.

This is deliberately NOT an Imara-invented number. It is Altman's Z''/EM-score for
non-manufacturers and emerging-market firms (Altman, 2005), computed by arithmetic
from the firm's own balance sheet — no LLM. When Z'' and the Imara band agree, that
is convergent evidence the Score is reading the firm correctly; when they diverge,
that is itself a finding worth surfacing.

    Z'' = 3.25 + 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
      X1 = Working Capital / Total Assets
      X2 = Retained Earnings / Total Assets
      X3 = EBIT / Total Assets
      X4 = Book Value of Equity / Total Liabilities

    Zones (EM): Safe > 2.6 | Grey 1.1–2.6 | Distress < 1.1
"""

SAFE_ABOVE = 2.6
DISTRESS_BELOW = 1.1

MODEL_NAME = "Altman Z''-score (emerging markets)"

# Imara band -> coarse distress tier, for the convergence cross-check.
_BAND_TIER = {"A": "safe", "B": "safe", "C": "grey", "D": "distress", "E": "distress"}


def _convergence(zone: str, imara_band: str) -> dict:
    tier = _BAND_TIER.get((imara_band or "").upper())
    if not tier:
        return {"agrees": None, "statement": "Imara band unavailable for comparison."}
    if tier == zone:
        return {"agrees": True,
                "statement": "The independent Z'' distress zone matches the Imara band — convergent evidence."}
    if {tier, zone} in ({"safe", "grey"}, {"grey", "distress"}):
        return {"agrees": True,
                "statement": "Z'' is one tier from the Imara band — broadly consistent."}
    return {"agrees": False,
            "statement": "Z'' and the Imara band diverge — review the financials; "
                         "one signal may be capturing something the other misses."}


def altman_z_em(figures: dict, imara_band: str = "") -> dict:
    """Compute the Altman Z''-EM score from extracted figures.

    Returns {available: False, reason} when the balance sheet is incomplete
    (e.g. only a P&L was uploaded) — Imara never fabricates the missing items.
    """
    f = figures or {}
    ta = f.get("total_assets")
    tl = f.get("total_liabilities")
    eq = f.get("equity")
    re_ = f.get("retained_earnings")
    ebit = f.get("operating_profit")
    ca = f.get("current_assets")
    cl = f.get("current_liabilities")

    # Fill what the accounting identity A = L + E lets us derive (no fabrication).
    if tl is None and ta is not None and eq is not None:
        tl = ta - eq
    if ta is None and tl is not None and eq is not None:
        ta = tl + eq
    if eq is None and ta is not None and tl is not None:
        eq = ta - tl

    missing = []
    if not ta:
        missing.append("total assets")
    if re_ is None:
        missing.append("retained earnings / accumulated reserves")
    if ebit is None:
        missing.append("EBIT (operating profit)")
    if tl is None or tl == 0:
        missing.append("total liabilities")
    if ca is None or cl is None:
        missing.append("current assets & current liabilities (working capital)")

    if missing:
        return {
            "available": False,
            "model": MODEL_NAME,
            "reason": "Needs a balance sheet — missing: " + ", ".join(missing) + ".",
        }

    wc = ca - cl
    x1 = wc / ta
    x2 = re_ / ta
    x3 = ebit / ta
    x4 = eq / tl
    z = 3.25 + 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4

    if z > SAFE_ABOVE:
        zone, label = "safe", "Safe"
    elif z >= DISTRESS_BELOW:
        zone, label = "grey", "Grey zone"
    else:
        zone, label = "distress", "Distress zone"

    return {
        "available": True,
        "model": MODEL_NAME,
        "z_score": round(z, 2),
        "zone": zone,
        "zone_label": label,
        "thresholds": {"safe_above": SAFE_ABOVE, "distress_below": DISTRESS_BELOW},
        "components": {
            "X1_working_capital_to_assets": round(x1, 3),
            "X2_retained_earnings_to_assets": round(x2, 3),
            "X3_ebit_to_assets": round(x3, 3),
            "X4_equity_to_liabilities": round(x4, 3),
        },
        "inputs": {
            "total_assets": ta, "total_liabilities": tl, "equity": eq,
            "retained_earnings": re_, "ebit": ebit, "working_capital": wc,
        },
        "convergence": _convergence(zone, imara_band),
        "note": ("Independent published distress model (arithmetic only). Used as an external "
                 "cross-check on the Imara Score, not as a component of it."),
    }
