"""
income_tax.py - deterministic SA individual income-tax computation.

Pure functions; the LLM only narrates. Brackets, rebates, the s11F retirement
cap and the s6A medical credits are REUSED from `relocation_tax` (the repo's
single dated source for these 2026/27 figures) rather than duplicated; the
travel rate-per-km comes from `sa_rates`. Re-verify every figure against the
current SARS tax tables each year of assessment.

Scope: salary + additional income, the s8(1)(b) travel-allowance deduction
(simplified prescribed-rate method) and PAYE inclusion, s11F retirement
deduction, age rebates and s6A medical credits, then PAYE already paid -> the
balance owing to / refundable by SARS. The full deemed-cost FIXED-COST table
(by vehicle value) is a later enhancement; this uses the prescribed rate per km.
"""

import math

from services import sa_rates
from services.relocation_tax import (
    SA_BRACKETS, SA_PRIMARY_REBATE, SA_SECONDARY_REBATE, SA_TERTIARY_REBATE,
    SA_RA_CAP, MEDICAL_CREDIT_MAIN, MEDICAL_CREDIT_ADDL,
)


def _num(v):
    try:
        f = float(v or 0)
    except (TypeError, ValueError):
        return 0.0
    # reject non-finite (inf/nan) so a hostile "1e400" can never propagate into
    # results or produce invalid JSON (Infinity/NaN) on the public endpoint.
    return f if (f > 0 and math.isfinite(f)) else 0.0


def tax_before_rebates(taxable):
    """Progressive SA PIT on taxable income, before any rebate."""
    t = _num(taxable)
    tax, lower = 0.0, 0.0
    for upper, rate in SA_BRACKETS:
        if t <= lower:
            break
        tax += (min(t, upper) - lower) * rate
        lower = upper
    return tax


def rebates(age=0):
    """Total age-based rebate (primary + secondary 65+ + tertiary 75+)."""
    a = int(_num(age))
    r = SA_PRIMARY_REBATE
    if a >= 65:
        r += SA_SECONDARY_REBATE
    if a >= 75:
        r += SA_TERTIARY_REBATE
    return r


def income_tax(taxable, age=0):
    """SA individual income tax on taxable income, net of age rebates (>= 0)."""
    return max(0.0, tax_before_rebates(taxable) - rebates(age))


def travel_paye_inclusion(allowance, business_use_ge_80pct=False):
    """Portion of a travel ALLOWANCE included in remuneration for PAYE (80% or 20%)."""
    frac = (sa_rates.TRAVEL_INCLUSION_BUSINESS if business_use_ge_80pct
            else sa_rates.TRAVEL_INCLUSION_DEFAULT)
    return round(_num(allowance) * frac, 2)


def travel_deduction(business_km, rate_per_km=None):
    """s8(1)(b) deduction against a travel allowance, simplified prescribed-rate method."""
    rate = sa_rates.TRAVEL_RATE_PER_KM if rate_per_km is None else float(rate_per_km)
    return round(_num(business_km) * rate, 2)


def medical_tax_credit(members):
    """Annual s6A medical-scheme-fees tax credit for a number of members on the scheme."""
    m = int(_num(members))
    if m <= 0:
        return 0.0
    monthly = MEDICAL_CREDIT_MAIN * min(m, 2) + MEDICAL_CREDIT_ADDL * max(0, m - 2)
    return round(monthly * 12, 2)


def assess(
    salary=0,
    annual_payment=0,
    commission=0,
    overtime=0,
    travel_allowance=0,
    additional_income=0,
    travel_business_km=0,
    retirement_contribution=0,
    medical_members=0,
    paye_paid=0,
    age=0,
):
    """Full-year individual assessment from IRP5-style inputs.

    Travel allowance is fully included in income, then reduced by the s8(1)(b)
    business-km deduction. Retirement contributions are deductible up to the
    lesser of the rand cap and 27.5% of income. Returns a structured breakdown
    plus the balance owing (positive) or refund (negative).
    """
    gross = sum(_num(x) for x in (salary, annual_payment, commission, overtime,
                                  travel_allowance, additional_income))
    ra_deduction = min(_num(retirement_contribution), SA_RA_CAP, 0.275 * gross)
    travel_ded = min(travel_deduction(travel_business_km), _num(travel_allowance))
    taxable = max(0.0, gross - ra_deduction - travel_ded)

    gross_tax = income_tax(taxable, age)
    med_credit = medical_tax_credit(medical_members)
    net_tax = max(0.0, gross_tax - med_credit)
    balance = net_tax - _num(paye_paid)

    return {
        "as_of": "SA 2026/27 tax year",
        "gross_income": round(gross, 2),
        "retirement_deduction": round(ra_deduction, 2),
        "travel_deduction": round(travel_ded, 2),
        "taxable_income": round(taxable, 2),
        "tax_before_credits": round(gross_tax, 2),
        "medical_tax_credit": med_credit,
        "tax_payable": round(net_tax, 2),
        "paye_paid": round(_num(paye_paid), 2),
        "balance": round(balance, 2),
        "position": ("owing" if balance > 0.005
                     else ("refund" if balance < -0.005 else "settled")),
    }
