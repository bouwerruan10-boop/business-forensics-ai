"""
provisional_tax.py - deterministic SA provisional-tax (IRP6) calculations.

Pure functions; the LLM only narrates. Tax on income is computed by the shared
`income_tax` engine; rates/thresholds come from the dated `sa_rates`. Implements
the Fourth Schedule mechanics: the first and second provisional payments, the
"basic amount" (with 8% p.a. escalation when the latest assessment is stale),
and the paragraph-20 under-estimation penalty. Decision-support, not advice.

Paragraph 20 (under-estimation) safe harbour, measured on the SECOND estimate:
- taxable income <= R1,000,000: safe if the estimate >= the LESSER of 90% of
  actual taxable income OR the basic amount.
- taxable income  > R1,000,000: safe if the estimate >= 80% of actual taxable
  income (the basic amount is ignored).
Penalty = 20% x (tax on the safe-harbour amount - tax already paid), floored at 0.
"""

from services import sa_rates
from services.income_tax import income_tax, _num


def basic_amount(latest_assessed_taxable, escalation_years=0):
    """The 'basic amount' = latest assessed taxable income, escalated 8% p.a. when
    the latest assessment is more than 18 months old (pass the number of full
    years to escalate; 0 = no escalation)."""
    base = _num(latest_assessed_taxable)
    n = max(0, int(_num(escalation_years)))
    return round(base * ((1 + sa_rates.PROV_BASIC_AMOUNT_ESCALATION) ** n), 2)


def first_payment(estimate_taxable, age=0, paye_paid=0):
    """First provisional payment: half the tax on the year's estimate, less PAYE
    attributable to the first half-year. Floored at 0."""
    half_tax = income_tax(estimate_taxable, age) * 0.5
    return round(max(0.0, half_tax - _num(paye_paid)), 2)


def second_payment(estimate_taxable, age=0, paye_paid=0, first_paid=0):
    """Second provisional payment: full-year tax on the estimate, less PAYE and the
    first payment already made. Floored at 0."""
    full = income_tax(estimate_taxable, age)
    return round(max(0.0, full - _num(paye_paid) - _num(first_paid)), 2)


def underestimation_penalty(actual_taxable, estimate_taxable, age=0,
                            basic_amt=0, tax_already_paid=0):
    """Paragraph-20 under-estimation penalty (0 if the estimate met the safe harbour)."""
    actual = _num(actual_taxable)
    if actual <= sa_rates.PROV_UNDERSTATE_THRESHOLD:
        ninety = sa_rates.PROV_SAFE_HARBOUR_LE_1M * actual
        basic = _num(basic_amt)
        # safe if estimate reaches the lesser of (90% of actual) or (basic amount);
        # use the lesser as the required taxable base. If no basic amount supplied,
        # fall back to the 90% line only.
        required_taxable = min(ninety, basic) if basic > 0 else ninety
    else:
        required_taxable = sa_rates.PROV_SAFE_HARBOUR_GT_1M * actual

    required_tax = income_tax(required_taxable, age)
    shortfall = max(0.0, required_tax - _num(tax_already_paid))
    return round(shortfall * sa_rates.PROV_PENALTY_RATE, 2)


def assess_provisional(estimate_taxable, age=0, paye_paid=0,
                       latest_assessed_taxable=0, escalation_years=0,
                       actual_taxable=None):
    """Full provisional picture: basic amount, the two payments, and (when the
    actual assessed taxable income is known) the under-estimation penalty and the
    balance owing on assessment."""
    basic = basic_amount(latest_assessed_taxable, escalation_years)
    p1 = first_payment(estimate_taxable, age, paye_paid * 0.5)
    p2 = second_payment(estimate_taxable, age, paye_paid, p1)
    out = {
        "as_of": "SA 2026/27 tax year",
        "basic_amount": basic,
        "tax_on_estimate": round(income_tax(estimate_taxable, age), 2),
        "first_payment": p1,
        "second_payment": p2,
        "total_provisional": round(p1 + p2, 2),
        "disclaimer": "Decision-support only - not tax advice; confirm with a tax practitioner.",
    }
    if actual_taxable is not None:
        full_tax = income_tax(actual_taxable, age)
        paid = p1 + p2 + _num(paye_paid)
        penalty = underestimation_penalty(actual_taxable, estimate_taxable, age,
                                           basic_amt=basic, tax_already_paid=paid)
        out["full_year_tax"] = round(full_tax, 2)
        out["tax_paid_to_date"] = round(paid, 2)
        out["underestimation_penalty"] = penalty
        out["balance_on_assessment"] = round(full_tax + penalty - paid, 2)
    return out
