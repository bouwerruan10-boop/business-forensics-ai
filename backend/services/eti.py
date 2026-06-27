"""
eti.py - deterministic SA Employment Tax Incentive (ETI) quantification.

Pure functions; the LLM only narrates. Bands are sourced from the dated
`sa_rates` module (effective 1 April 2025; ETI Act 26 of 2013 as amended,
per the SARS "ETI changes with effect from 1 April 2025" notice).

A qualifying employee is generally aged 18-29 and earns < R7,500/month. The
employer must also meet the registration / minimum-wage / minimum-hours rules
(NMW, 160-hour pro-rata) — those are assumed met here and flagged in the output,
since they cannot be derived from age + wage alone.
"""

from services import sa_rates


def monthly_eti(remuneration, year=1):
    """ETI rand value for ONE qualifying employee in ONE month.

    `year` is 1 for the first 12 qualifying months, 2 for the second 12.
    Returns 0.0 for remuneration <= 0 or >= the R7,500 ceiling.
    """
    r = float(remuneration or 0)
    if r <= 0 or r >= sa_rates.ETI_EARN_CEILING:
        return 0.0

    first = year != 2  # any year other than 2 is treated as the first-12-months rate
    if r < sa_rates.ETI_BAND1_CEILING:                      # R0 - 2,499.99
        rate = sa_rates.ETI_BAND1_RATE_Y1 if first else sa_rates.ETI_BAND1_RATE_Y2
        return round(r * rate, 2)
    if r < sa_rates.ETI_BAND2_CEILING:                      # R2,500 - 5,499.99
        return sa_rates.ETI_BAND2_FLAT_Y1 if first else sa_rates.ETI_BAND2_FLAT_Y2

    # R5,500 - 7,499.99 : taper down to nil at R7,500
    flat = sa_rates.ETI_BAND2_FLAT_Y1 if first else sa_rates.ETI_BAND2_FLAT_Y2
    taper = sa_rates.ETI_TAPER_RATE_Y1 if first else sa_rates.ETI_TAPER_RATE_Y2
    return round(max(0.0, flat - taper * (r - sa_rates.ETI_BAND2_CEILING)), 2)


def _age_eligible(age):
    try:
        a = int(age)
    except (TypeError, ValueError):
        return False
    return sa_rates.ETI_AGE_MIN <= a <= sa_rates.ETI_AGE_MAX


def quantify_eti(employees, year=1):
    """Quantify ETI across a roster.

    `employees` is a list of dicts with at least `age` and `monthly_remuneration`
    (or `remuneration`). Returns per-employee detail plus the monthly total and a
    12-month projection (if every qualifying month is claimed at this level).
    """
    rows = []
    monthly_total = 0.0
    qualifying = 0
    for emp in (employees or []):
        if not isinstance(emp, dict):
            emp = {}
        age = emp.get("age")
        remun = emp.get("monthly_remuneration", emp.get("remuneration", 0))
        age_ok = _age_eligible(age)
        r = float(remun or 0)
        if not age_ok:
            value, reason = 0.0, "not eligible: age outside 18-29"
        elif r <= 0:
            value, reason = 0.0, "no remuneration supplied"
        elif r >= sa_rates.ETI_EARN_CEILING:
            value, reason = 0.0, "not eligible: earns R7,500/month or more"
        else:
            value = monthly_eti(r, year)
            reason = "qualifying"
            qualifying += 1
            monthly_total += value
        rows.append({
            "age": age,
            "monthly_remuneration": round(r, 2),
            "age_eligible": age_ok,
            "monthly_eti": round(value, 2),
            "reason": reason,
        })

    return {
        "as_of": sa_rates.AS_OF,
        "year": 2 if year == 2 else 1,
        "employees": rows,
        "qualifying_count": qualifying,
        "monthly_total": round(monthly_total, 2),
        "annual_projection": round(monthly_total * 12, 2),
        "note": (
            "ETI is claimed monthly via EMP201 per qualifying employee (age 18-29, "
            "remuneration < R7,500/month). The employer must also meet registration, "
            "minimum-wage and minimum-hours (160h pro-rata) rules - assumed met here."
        ),
    }
