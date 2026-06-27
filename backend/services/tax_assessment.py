"""
tax_assessment.py - orchestrates the deterministic SA tax engines for the
public /api/tax/income endpoint.

Pure + side-effect-free: takes a request body (dict) and returns a combined,
decision-support tax assessment (individual income tax + VAT position + ETI),
each computed by its own deterministic engine. Only known keys are forwarded to
each engine, so an arbitrary/hostile body can never raise a TypeError. Not tax
advice; figures are SARS 2026/27 and must be confirmed with a practitioner.
"""

from services import (
    income_tax, vat_calc, eti, provisional_tax, cgt, fringe_benefits, lump_sum,
    assessed_losses, tax_residency, exit_tax, foreign_income,
)

_INCOME_KEYS = (
    "salary", "annual_payment", "commission", "overtime", "travel_allowance",
    "additional_income", "travel_business_km", "retirement_contribution",
    "medical_members", "paye_paid", "age",
)
_VAT_KEYS = (
    "standard_rated_incl", "standard_rated_excl", "zero_rated", "exempt",
    "input_capital_incl", "input_other_incl", "output_adjustments", "input_adjustments",
)

_CGT_KEYS = (
    "total_gains", "total_losses", "taxpayer", "primary_residence_gain",
    "year_of_death", "other_taxable_income", "age",
)
_PROV_KEYS = (
    "estimate_taxable", "age", "paye_paid", "latest_assessed_taxable",
    "escalation_years", "actual_taxable",
)

_FRINGE_KEYS = (
    "car_determined_value", "car_has_maintenance", "loan_amount",
    "loan_interest_paid_pct", "accommodation_remuneration_proxy",
)
_LUMP_KEYS = ("amount", "kind", "prior")
_LOSS_KEYS = (
    "taxable_income_before", "balance_brought_forward", "taxpayer",
    "suspect_trade", "fails_facts_test",
)
_RESIDENCY_KEYS = ("current_year_days", "prior_years_days", "days_continuously_absent")
_EXIT_KEYS = ("deemed_gains", "taxpayer", "total_losses", "other_taxable_income", "age")
_FOREIGN_KEYS = ("foreign_employment_income", "days_outside_total", "longest_continuous_days")

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

    fringe = _pick(body.get("fringe_benefits"), _FRINGE_KEYS)
    if fringe:
        out["fringe_benefits"] = fringe_benefits.assess_fringe_benefits(**fringe)

    lump = _pick(body.get("lump_sum"), _LUMP_KEYS)
    if lump and lump.get("amount"):
        out["lump_sum"] = lump_sum.assess_lump_sum(**lump)

    cgt_in = _pick(body.get("cgt"), _CGT_KEYS)
    if cgt_in:
        out["cgt"] = cgt.assess_cgt(**cgt_in)

    prov = _pick(body.get("provisional"), _PROV_KEYS)
    if prov:
        out["provisional"] = provisional_tax.assess_provisional(**prov)

    loss = _pick(body.get("assessed_loss"), _LOSS_KEYS)
    if loss and (loss.get("balance_brought_forward") or loss.get("taxable_income_before")):
        out["assessed_loss"] = assessed_losses.assess_assessed_loss(**loss)

    residency = _pick(body.get("residency"), _RESIDENCY_KEYS)
    if residency and residency.get("current_year_days") is not None:
        out["residency"] = tax_residency.physical_presence_test(**residency)

    exit_in = _pick(body.get("exit_tax"), _EXIT_KEYS)
    if exit_in and exit_in.get("deemed_gains"):
        out["exit_tax"] = exit_tax.assess_exit_tax(**exit_in)

    foreign = _pick(body.get("foreign_income"), _FOREIGN_KEYS)
    if foreign and foreign.get("foreign_employment_income"):
        out["foreign_income"] = foreign_income.assess_foreign_employment(**foreign)

    return out
