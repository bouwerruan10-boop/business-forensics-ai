"""
sars_rate_manifest.py - the single mapping between Imara's hardcoded rates and SARS.

Pure / no network. Each entry says, for one figure Imara depends on: which SARS page
publishes it, the stable text label(s) to anchor on, the EXPECTED value (read LIVE from
sa_rates / relocation_tax so there is no second source of truth), the unit, a sanity
range, and the statutory citation. The diff engine (sars_rate_check.py) parses the
supplied SARS page text, finds each value by its anchors, and compares to `expected` -
flagging drift for HUMAN review (it never edits a figure).

Coverage (v1): the cleanly-anchorable, high-value figures - rebates, VAT, CGT, company/
trust rates, the ETI earnings ceiling, and the two volatile interest rates (PDF tables).
Re-verify every value against SARS before relying on it.
"""

from services import sa_rates
from services import relocation_tax

# SARS page ids -> the URL that publishes the figures (for reference + the fetch helper).
PAGES = {
    "individuals": "https://www.sars.gov.za/tax-rates/income-tax/rates-of-tax-for-individuals/",
    "vat": "https://www.sars.gov.za/types-of-tax/value-added-tax/",
    "cgt": "https://www.sars.gov.za/tax-rates/income-tax/capital-gains-tax-cgt/",
    "companies": "https://www.sars.gov.za/tax-rates/income-tax/companies-trusts-and-small-business-corporations-sbc/",
    "eti": "https://www.sars.gov.za/types-of-tax/pay-as-you-earn/employment-tax-incentive-eti/",
    "interest": "https://www.sars.gov.za/legal-counsel/legal-counsel-publications/tables-of-interest-rates/",
}


def manifest():
    """Return the list of figures to check, with EXPECTED read live from code. Pure."""
    return [
        {"key": "primary_rebate", "label": "Primary rebate", "page": "individuals",
         "anchors": ["primary rebate"], "unit": "zar",
         "expected": float(relocation_tax.SA_PRIMARY_REBATE), "sanity": (10000, 30000),
         "citation": "Income Tax Act 58/1962 s6(2)(a)"},
        {"key": "secondary_rebate", "label": "Secondary rebate (65-74)", "page": "individuals",
         "anchors": ["secondary rebate"], "unit": "zar",
         "expected": float(relocation_tax.SA_SECONDARY_REBATE), "sanity": (5000, 20000),
         "citation": "Income Tax Act 58/1962 s6(2)(b)"},
        {"key": "tertiary_rebate", "label": "Tertiary rebate (75+)", "page": "individuals",
         "anchors": ["tertiary rebate"], "unit": "zar",
         "expected": float(relocation_tax.SA_TERTIARY_REBATE), "sanity": (1000, 10000),
         "citation": "Income Tax Act 58/1962 s6(2)(c)"},

        {"key": "vat_rate", "label": "VAT standard rate", "page": "vat",
         "anchors": ["standard rate", "rate of 15", "vat is levied"], "unit": "percent",
         "expected": float(sa_rates.VAT_RATE), "sanity": (10, 25),
         "citation": "VAT Act 89/1991 s7(1)(a)"},
        {"key": "vat_compulsory_threshold", "label": "VAT compulsory registration threshold", "page": "vat",
         "anchors": ["compulsory", "exceed", "12-month"], "unit": "zar",
         "expected": float(sa_rates.VAT_COMPULSORY_THRESHOLD), "sanity": (500_000, 5_000_000),
         "citation": "VAT Act 89/1991 s23"},

        {"key": "cgt_inclusion_individual", "label": "CGT inclusion rate (individual)", "page": "cgt",
         "anchors": ["inclusion rate", "40%", "individuals"], "unit": "percent",
         "expected": float(sa_rates.CGT_INCLUSION_INDIVIDUAL) * 100, "sanity": (20, 100),
         "citation": "Income Tax Act 58/1962 8th Schedule"},
        {"key": "cgt_annual_exclusion", "label": "CGT annual exclusion", "page": "cgt",
         "anchors": ["annual exclusion"], "unit": "zar",
         "expected": float(sa_rates.CGT_ANNUAL_EXCLUSION), "sanity": (20_000, 100_000),
         "citation": "Income Tax Act 58/1962 8th Schedule par 5"},

        {"key": "company_flat_rate", "label": "Company income-tax rate", "page": "companies",
         "anchors": ["companies", "27%", "27 per cent"], "unit": "percent",
         "expected": float(sa_rates.COMPANY_FLAT_RATE), "sanity": (15, 40),
         "citation": "Income Tax Act 58/1962 s5"},
        {"key": "trust_flat_rate", "label": "Trust income-tax rate", "page": "companies",
         "anchors": ["trusts", "45%", "other than a special trust"], "unit": "percent",
         "expected": float(sa_rates.TRUST_FLAT_RATE), "sanity": (30, 50),
         "citation": "Income Tax Act 58/1962 s5"},

        {"key": "eti_earn_ceiling", "label": "ETI maximum monthly remuneration", "page": "eti",
         "anchors": ["maximum monthly remuneration", "monthly remuneration", "7 500", "7,500"],
         "unit": "zar", "expected": float(sa_rates.ETI_EARN_CEILING), "sanity": (5_000, 15_000),
         "citation": "Employment Tax Incentive Act 26/2013"},

        {"key": "official_rate_of_interest", "label": "Official rate of interest (fringe-benefit loans)",
         "page": "interest", "anchors": ["official rate of interest", "interest-free or low interest"],
         "unit": "percent", "expected": float(sa_rates.OFFICIAL_RATE_OF_INTEREST), "sanity": (4, 15),
         "citation": "Income Tax Act 58/1962 7th Schedule; SARS Interest Rate Table 3"},
        {"key": "sars_interest_rate", "label": "Interest on outstanding tax", "page": "interest",
         "anchors": ["outstanding taxes", "interest rate on outstanding"], "unit": "percent",
         "expected": float(sa_rates.SARS_INTEREST_RATE), "sanity": (5, 18),
         "citation": "Tax Administration Act 28/2011 s89; SARS Interest Rate Table 1"},
    ]


def manifest_summary():
    """Lightweight view of what is checked (for the admin surface)."""
    m = manifest()
    return {"count": len(m), "pages": PAGES,
            "figures": [{"key": e["key"], "label": e["label"], "page": e["page"],
                         "expected": e["expected"], "unit": e["unit"]} for e in m]}
