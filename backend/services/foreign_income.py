"""
foreign_income.py - deterministic SA foreign-employment income exemption (s10(1)(o)(ii)).

Pure functions; the LLM only narrates. A SA tax resident's foreign EMPLOYMENT
income is exempt up to a cap (R1.25m) where they render services outside SA for:
  - more than 183 days in aggregate in any 12-month period, INCLUDING
  - a continuous period of more than 60 full days outside SA in that period.
Income above the cap is taxed normally; the exemption applies to remuneration for
services rendered abroad (not to investment income). Thresholds + cap come from the
dated `sa_rates`. Re-verify yearly. Decision-support, not advice.
"""

from services import sa_rates
from services.income_tax import _num


def _int(v):
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return 0
    return n if n > 0 else 0


def assess_foreign_employment(foreign_employment_income, days_outside_total,
                              longest_continuous_days, **_ignored):
    """Compute the s10(1)(o)(ii) exemption on foreign employment income."""
    income = _num(foreign_employment_income)
    total = _int(days_outside_total)
    cont = _int(longest_continuous_days)

    total_ok = total > sa_rates.FOREIGN_DAYS_TOTAL_MIN
    cont_ok = cont > sa_rates.FOREIGN_DAYS_CONTINUOUS_MIN
    qualifies = bool(total_ok and cont_ok)

    cap = sa_rates.FOREIGN_EMPLOYMENT_EXEMPTION_CAP
    exempt = round(min(income, cap), 2) if qualifies else 0.0
    taxable = round(income - exempt, 2)

    if qualifies:
        summary = ("Qualifies for the s10(1)(o)(ii) exemption: the first R{:,.0f} of foreign employment "
                   "income is exempt; R{:,.0f} remains taxable in SA.").format(cap, taxable)
    else:
        missing = []
        if not total_ok:
            missing.append("more than 183 days outside SA in the 12-month period")
        if not cont_ok:
            missing.append("a continuous period of more than 60 full days outside SA")
        summary = ("Does NOT qualify - the day-count is not met (need " + " and ".join(missing) +
                   "). All R{:,.0f} of the foreign employment income is taxable in SA.").format(income)

    return {
        "as_of": "SA 2026/27 (Income Tax Act s10(1)(o)(ii))",
        "foreign_employment_income": round(income, 2),
        "exemption_cap": cap,
        "qualifies": qualifies,
        "days_outside_total": total,
        "days_continuous": cont,
        "days_test": {
            "total_over_183": total_ok,
            "continuous_over_60": cont_ok,
        },
        "exempt_amount": exempt,
        "taxable_amount": taxable,
        "summary": summary,
        "disclaimer": ("Decision-support only - not tax advice. The exemption is for EMPLOYMENT income for "
                       "services rendered abroad; confirm with a cross-border tax practitioner."),
    }
