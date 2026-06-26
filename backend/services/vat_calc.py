"""
vat_calc.py - deterministic South African VAT computations.

Pure functions only; every figure is computed here and the LLM merely narrates.
The VAT rate and registration thresholds are sourced from the dated `sa_rates`
module so a rate change is made in exactly one place.

The "tax fraction" on a VAT-inclusive amount is the standard SARS fraction
rate / (100 + rate) = 15/115 at the current 15% rate.

Citations (re-verify against the VAT Act 89 of 1991, the SARS VAT 404 guide and
the live VAT201 return whenever the rate or fields change):
- VAT standard rate + compulsory/voluntary registration thresholds:
  services.sa_rates (carries its own AS_OF date).
- Output tax  = VAT on standard-rated supplies (zero-rated and exempt = nil output).
- Input tax   = VAT incurred on capital goods + other goods/services acquired
  for taxable supplies (the VAT201 splits capital vs other input).
- Net VAT     = output tax - input tax; positive is payable to SARS, negative is
  a refund.
"""

from services import sa_rates


def _f(x):
    """Coerce to a non-negative float; None/blank/garbage -> 0.0."""
    try:
        v = float(x or 0)
    except (TypeError, ValueError):
        return 0.0
    return v if v > 0 else 0.0


def _rate(rate):
    return sa_rates.VAT_RATE if rate is None else float(rate)


def tax_fraction(rate=None):
    """VAT-inclusive tax fraction: rate / (100 + rate) (= 15/115 at 15%)."""
    r = _rate(rate)
    return r / (100.0 + r)


def split_inclusive(amount_incl, rate=None):
    """Split a VAT-inclusive amount into {excl, vat, incl}."""
    incl = _f(amount_incl)
    vat = incl * tax_fraction(rate)
    return {
        "incl": round(incl, 2),
        "vat": round(vat, 2),
        "excl": round(incl - vat, 2),
    }


def add_vat(amount_excl, rate=None):
    """Add VAT to a VAT-exclusive amount: {excl, vat, incl}."""
    excl = _f(amount_excl)
    vat = excl * _rate(rate) / 100.0
    return {
        "excl": round(excl, 2),
        "vat": round(vat, 2),
        "incl": round(excl + vat, 2),
    }


def compute_vat201(
    standard_rated_incl=0,
    standard_rated_excl=0,
    zero_rated=0,
    exempt=0,
    input_capital_incl=0,
    input_other_incl=0,
    output_adjustments=0,
    input_adjustments=0,
    rate=None,
):
    """Compute a VAT201-style net VAT position from period figures.

    Standard-rated supplies may be supplied VAT-inclusive and/or VAT-exclusive;
    both are accepted and combined. Zero-rated and exempt supplies carry no
    output tax (they are reported for completeness only). Input tax is split into
    capital goods vs other goods/services to mirror the VAT201 fields. Optional
    output/input adjustments cover items such as change-in-use and bad debts.

    Returns a structured dict; net_vat_payable > 0 means pay SARS, < 0 is a refund.
    """
    r = _rate(rate)
    frac = tax_fraction(r)

    sr_incl = _f(standard_rated_incl)
    sr_excl = _f(standard_rated_excl)
    output_vat = sr_incl * frac + sr_excl * r / 100.0 + _f(output_adjustments)

    cap_vat = _f(input_capital_incl) * frac
    other_vat = _f(input_other_incl) * frac
    total_input_vat = cap_vat + other_vat + _f(input_adjustments)

    net = output_vat - total_input_vat
    if abs(net) < 0.005:
        position = "nil"
    elif net > 0:
        position = "payable"
    else:
        position = "refund"

    standard_rated_supplies_excl = (sr_incl - sr_incl * frac) + sr_excl

    return {
        "as_of": sa_rates.AS_OF,
        "rate": r,
        "tax_fraction_label": "{:.0f}/{:.0f}".format(r, 100.0 + r),
        "tax_fraction": round(frac, 6),
        "output": {
            "standard_rated_supplies_excl": round(standard_rated_supplies_excl, 2),
            "output_vat": round(output_vat, 2),
            "zero_rated_supplies": round(_f(zero_rated), 2),
            "exempt_supplies": round(_f(exempt), 2),
        },
        "input": {
            "capital_goods_vat": round(cap_vat, 2),
            "other_goods_services_vat": round(other_vat, 2),
            "total_input_vat": round(total_input_vat, 2),
        },
        "net_vat_payable": round(net, 2),
        "net_position": position,
    }
