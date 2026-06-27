"""
exit_tax.py - deterministic SA exit tax (section 9H deemed disposal).

Pure functions; the LLM only narrates. When a person CEASES to be a SA tax
resident, s9H deems a disposal of their WORLDWIDE assets at market value on the
day before cessation - a CGT event. Key EXCLUSIONS that are NOT deemed disposed
(they stay in the SA CGT net and are taxed only on an actual future sale):
SA immovable property, assets of a SA permanent establishment, and certain
retirement/equity-instrument interests.

This engine REUSES services/cgt.py: the s9H deemed gain is just a capital gain,
taxed at the taxpayer's CGT rate. Provide the aggregate deemed gain on the assets
that ARE subject to s9H (i.e. exclude SA immovable property). Re-verify yearly.
Decision-support, not advice; formalise cessation with SARS (RAV01).
"""

from services import cgt
from services.income_tax import _num


def assess_exit_tax(deemed_gains, taxpayer="individual", total_losses=0,
                    other_taxable_income=0, age=0, **_ignored):
    """Compute the s9H exit CGT on the deemed disposal of worldwide assets.

    `deemed_gains` is the aggregate capital gain on assets SUBJECT to s9H (exclude
    SA immovable property and other excluded assets). Reuses the CGT engine.
    """
    gains = _num(deemed_gains)
    base = cgt.assess_cgt(total_gains=gains, total_losses=total_losses,
                          taxpayer=taxpayer, other_taxable_income=other_taxable_income, age=age)
    return {
        "as_of": "SA 2026/27 (Income Tax Act s9H)",
        "taxpayer": base["taxpayer"],
        "deemed_gains": round(gains, 2),
        "net_capital_gain": base["net_capital_gain"],
        "taxable_capital_gain": base["taxable_capital_gain"],
        "inclusion_rate": base["inclusion_rate"],
        "exit_tax_payable": base["cgt_payable"],
        "effective_rate_pct": base["effective_rate_pct"],
        "excluded_assets_note": ("SA immovable property, SA permanent-establishment assets and certain "
                                 "retirement interests are NOT deemed disposed under s9H - exclude them from "
                                 "the deemed gain above; they remain taxable in SA only on an actual future sale."),
        "process_note": ("Ceasing residency must be formalised with SARS (RAV01 on eFiling, capturing the "
                         "cessation date). The s9H charge falls in the year of cessation; the second deemed "
                         "year-of-assessment split may apply - confirm the timing with a practitioner."),
        "disclaimer": "Decision-support only - not tax advice; confirm with a cross-border tax practitioner.",
    }
