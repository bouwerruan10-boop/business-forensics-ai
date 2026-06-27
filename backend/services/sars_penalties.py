"""
sars_penalties.py - deterministic SARS penalty + interest engine.

Pure functions; the LLM only narrates. Covers the Tax Administration Act
machinery around an assessment:
- s210/211 administrative non-compliance penalty (fixed-amount monthly table),
- s222/223 understatement penalty (the behaviour x case percentage table),
- s187-189 interest on outstanding tax (prescribed rate from sa_rates),
- a generic late-payment penalty (e.g. provisional par 27 = 10%).

Plus an "exposure band" helper (audit-risk -> likely understatement-penalty
behaviour -> a rand range) so Imara can show a defensible exposure range rather
than a fabricated single number. Re-verify the tables against the current SARS
Understatement Penalty Guide + the s211 public notice before relying on them.
"""

from services import sa_rates

# ── s211 administrative non-compliance penalty: monthly fixed amount by the
#    preceding year's taxable income (assessed loss -> the lowest bracket).
#    (upper_bound_of_taxable_income, monthly_rand). Recurs up to 35 months.
ADMIN_PENALTY_TABLE = [
    (250_000, 250),
    (500_000, 500),
    (1_000_000, 1_000),
    (5_000_000, 2_000),
    (10_000_000, 4_000),
    (50_000_000, 8_000),
    (float("inf"), 16_000),
]
ADMIN_PENALTY_MAX_MONTHS = 35

# ── s223 understatement penalty table: behaviour (rows) x case (columns), %.
USP_TABLE = {
    "substantial_understatement": {"standard": 10, "repeat": 20, "vd_after": 5, "vd_before": 0},
    "reasonable_care_not_taken":  {"standard": 25, "repeat": 50, "vd_after": 15, "vd_before": 0},
    "no_reasonable_grounds":      {"standard": 50, "repeat": 75, "vd_after": 25, "vd_before": 0},
    "impermissible_avoidance":    {"standard": 75, "repeat": 100, "vd_after": 35, "vd_before": 0},
    "gross_negligence":           {"standard": 100, "repeat": 125, "vd_after": 50, "vd_before": 5},
    "intentional_tax_evasion":    {"standard": 150, "repeat": 200, "vd_after": 75, "vd_before": 10},
}

# Audit-risk level -> a (low, high) behaviour range for an exposure band (C3).
_EXPOSURE_BANDS = {
    "low": ("substantial_understatement", "reasonable_care_not_taken"),
    "medium": ("reasonable_care_not_taken", "no_reasonable_grounds"),
    "high": ("no_reasonable_grounds", "gross_negligence"),
}


def _num(x):
    try:
        v = float(x or 0)
    except (TypeError, ValueError):
        return 0.0
    return v


def admin_penalty(preceding_taxable_income, months_outstanding=1):
    """s211 administrative penalty for late/outstanding returns."""
    ti = _num(preceding_taxable_income)
    monthly = ADMIN_PENALTY_TABLE[-1][1]
    for upper, amount in ADMIN_PENALTY_TABLE:
        if ti <= upper:
            monthly = amount
            break
    months = max(0, min(int(_num(months_outstanding)), ADMIN_PENALTY_MAX_MONTHS))
    return {
        "monthly": monthly,
        "months": months,
        "total": monthly * months,
        "capped_at_months": ADMIN_PENALTY_MAX_MONTHS,
    }


def understatement_penalty(shortfall, behaviour="substantial_understatement", case="standard"):
    """s223 understatement penalty = percentage x the shortfall (the tax effect)."""
    pct = USP_TABLE.get(behaviour, USP_TABLE["substantial_understatement"]).get(case, 0)
    s = max(0.0, _num(shortfall))
    return {"behaviour": behaviour, "case": case, "percentage": pct,
            "penalty": round(s * pct / 100.0, 2)}


def usp_exposure(shortfall, risk_level="low"):
    """Exposure BAND (not a single number): map an audit-risk level to a likely
    understatement-penalty behaviour range and the rand range on the shortfall."""
    lo_beh, hi_beh = _EXPOSURE_BANDS.get(risk_level, _EXPOSURE_BANDS["low"])
    lo_pct = USP_TABLE[lo_beh]["standard"]
    hi_pct = USP_TABLE[hi_beh]["standard"]
    s = max(0.0, _num(shortfall))
    return {
        "risk_level": risk_level if risk_level in _EXPOSURE_BANDS else "low",
        "low_behaviour": lo_beh, "high_behaviour": hi_beh,
        "low_percentage": lo_pct, "high_percentage": hi_pct,
        "low_penalty": round(s * lo_pct / 100.0, 2),
        "high_penalty": round(s * hi_pct / 100.0, 2),
        "note": ("Indicative exposure RANGE only - the actual understatement penalty "
                 "depends on SARS's view of the behaviour (s223) and any voluntary "
                 "disclosure. Keep contemporaneous records and reasonable grounds for "
                 "every position to stay at the low end."),
    }


def interest_on_tax(amount, days, annual_rate=None):
    """Simple interest on outstanding tax (s187-189), prescribed rate from sa_rates."""
    rate = sa_rates.SARS_INTEREST_RATE if annual_rate is None else float(annual_rate)
    return round(max(0.0, _num(amount)) * rate / 100.0 * max(0, int(_num(days))) / 365.0, 2)


def late_payment_penalty(amount, rate_pct=10.0):
    """Generic fixed-percentage late-payment penalty (e.g. provisional par 27 = 10%)."""
    return round(max(0.0, _num(amount)) * float(rate_pct) / 100.0, 2)
