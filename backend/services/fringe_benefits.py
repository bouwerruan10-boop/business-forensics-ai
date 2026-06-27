"""
fringe_benefits.py - deterministic SA fringe-benefit values (7th Schedule).

Pure functions; the LLM only narrates. Covers the common SME fringe benefits:
- right of use of a company motor vehicle (par 7): 3.5%/month of determined
  value, 3.25% if a maintenance plan is in place;
- low-interest / interest-free loan (par 11): the shortfall vs the s1 "official
  rate of interest" (repo + 1%, from sa_rates);
- free/cheap residential accommodation (par 9): the lower of the rental-value
  formula (A-B) x C/100 x D/12 and the cost to the employer.
Re-verify the rates + the accommodation abatement against the SARS Guide for
Employers in respect of Fringe Benefits each year.
"""

from services import sa_rates

CAR_RATE = 3.5                 # % of determined value per month
CAR_RATE_WITH_MAINTENANCE = 3.25
ACCOMMODATION_ABATEMENT = 91_250   # the "B" in the par 9 formula (verify yearly)


def _num(x):
    try:
        v = float(x or 0)
    except (TypeError, ValueError):
        return 0.0
    return v if v > 0 else 0.0


def company_car_benefit(determined_value, has_maintenance_plan=False, months=12):
    """Right-of-use of a company car: % of determined value per month."""
    rate = CAR_RATE_WITH_MAINTENANCE if has_maintenance_plan else CAR_RATE
    m = max(0, min(int(_num(months)), 12))
    return round(_num(determined_value) * rate / 100.0 * m, 2)


def low_interest_loan_benefit(loan_amount, interest_rate_paid_pct=0, official_rate=None):
    """Annual taxable benefit = (official rate - rate actually paid) x loan."""
    official = sa_rates.OFFICIAL_RATE_OF_INTEREST if official_rate is None else float(official_rate)
    diff = max(0.0, official - _num(interest_rate_paid_pct))
    return round(_num(loan_amount) * diff / 100.0, 2)


def accommodation_benefit(remuneration_proxy, cost_to_employer=None,
                          furnished=False, employer_supplies_power=False,
                          employer_owned=True, months=12):
    """Par 9 residential-accommodation benefit: lower of the rental-value formula
    and the cost to the employer (where the employer does not own the property)."""
    a = _num(remuneration_proxy)
    c = 17.0
    if furnished and employer_supplies_power:
        c = 19.0
    elif furnished or employer_supplies_power:
        c = 18.0
    m = max(0, min(int(_num(months)), 12))
    formula = max(0.0, a - ACCOMMODATION_ABATEMENT) * c / 100.0 * m / 12.0
    formula = round(formula, 2)
    if not employer_owned and cost_to_employer is not None:
        return min(formula, round(_num(cost_to_employer), 2))
    return formula


def assess_fringe_benefits(car_determined_value=0, car_has_maintenance=False,
                           loan_amount=0, loan_interest_paid_pct=0,
                           accommodation_remuneration_proxy=0, **_ignored):
    """Aggregate the common fringe benefits into a single taxable total (annual)."""
    car = company_car_benefit(car_determined_value, car_has_maintenance)
    loan = low_interest_loan_benefit(loan_amount, loan_interest_paid_pct)
    accom = accommodation_benefit(accommodation_remuneration_proxy) if _num(accommodation_remuneration_proxy) else 0.0
    total = round(car + loan + accom, 2)
    return {
        "as_of": "SA 2026/27 tax year",
        "company_car": car,
        "low_interest_loan": loan,
        "accommodation": accom,
        "total_taxable_fringe_benefits": total,
        "official_rate_used": sa_rates.OFFICIAL_RATE_OF_INTEREST,
        "disclaimer": "Decision-support only - not tax advice; confirm with a tax practitioner.",
    }
