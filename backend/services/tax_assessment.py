"""
tax_assessment.py - orchestrates the deterministic SA tax engines for the
public /api/tax/income endpoint.

Pure + side-effect-free: takes a request body (dict) and returns a combined,
decision-support tax assessment (individual income tax + VAT position + ETI),
each computed by its own deterministic engine. Only known keys are forwarded to
each engine, so an arbitrary/hostile body can never raise a TypeError. Not tax
advice; figures are SARS 2026/27 and must be confirmed with a practitioner.
"""

from services import income_tax, vat_calc, eti

_INCOME_KEYS = (
    "salary", "annual_payment", "commission", "overtime", "travel_allowance",
    "additional_income", "travel_business_km", "retirement_contribution",
    "medical_members", "paye_paid", "age",
)
_VAT_KEYS = (
    "standard_rated_incl", "standard_rated_excl", "zero_rated", "exempt",
    "input_capital_incl", "input_other_incl", "output_adjustments", "input_adjustments",
)

_DISCLAIMER = (
    "Decision-support only - not tax advice. Figures are SARS 2026/27; confirm "
    "every result with a registered tax practitioner before filing."
)


def _pick(d, keys):
    d = d if isinstance(d, dict) else {}
    return {k: d[k] for k in keys if k in d}


def assess_all(body):
    """Build the combined tax assessment from a request body.

    Recognised sections: `income` (IRP5-style fields), `vat` (period figures),
    `employees` (roster for ETI) + optional `eti_year`. Sections with no input
    are omitted from the response.
    """
    body = body if isinstance(body, dict) else {}
    out = {"as_of": "SA 2026/27 tax year", "disclaimer": _DISCLAIMER}

    income = _pick(body.get("income"), _INCOME_KEYS)
    if income:
        out["income_tax"] = income_tax.assess(**income)

    vat = _pick(body.get("vat"), _VAT_KEYS)
    if vat:
        out["vat"] = vat_calc.compute_vat201(**vat)

    employees = body.get("employees")
    if isinstance(employees, list) and employees:
        year = 2 if body.get("eti_year") == 2 else 1
        out["eti"] = eti.quantify_eti(employees, year=year)

    return out
