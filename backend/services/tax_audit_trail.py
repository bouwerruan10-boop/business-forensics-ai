"""
tax_audit_trail.py - examination-survivable provenance for every computed tax figure.

Pure functions for the trail; a thin DB wrapper for the immutable record. The
2026-06-28 strategic research (Thread 5) named this moat layer #1: "every number
reproducible and cited to the specific SARS provision." Imara's tax engines already
compute deterministically from dated `sa_rates` constants; this surfaces, per result
section, the EXACT statutory provision, the dated rate source, and the headline
figures - so an auditor or SARS can trace how each number was derived. Optionally the
whole trail is written to the tamper-evident decision-audit hash chain, making it
reproducible and immutable.

Decision-support, not tax advice. Re-verify every citation against SARS each year.
"""

from services import sa_rates

# Curated statutory provenance for each tax-assessment section (keys mirror
# services/tax_assessment.assess_all). Authored from the engine implementations;
# `figures` are the headline outputs an auditor would trace.
_TAX_CITATIONS = {
    "income_tax": {
        "provision": ("Income Tax Act 58/1962 - s5/s6 (rates & rebates), s8(1)(b) (travel allowance), "
                      "s11F (retirement), s6A/s6B (medical tax credits), 4th Schedule (PAYE)"),
        "rate_source": "SARS 2026/27 individual tax tables, rebates and medical credits",
        "figures": ("gross_income", "taxable_income", "tax_before_credits", "tax_payable", "balance"),
    },
    "vat": {
        "provision": "VAT Act 89/1991 - s7(1)(a) (15% standard rate), s16/s17 (input tax), s23 (registration)",
        "rate_source": "Standard VAT rate 15% (tax fraction 15/115)",
        "figures": ("net_vat_payable", "net_position"),
    },
    "eti": {
        "provision": "Employment Tax Incentive Act 26/2013 (as amended)",
        "rate_source": "SARS ETI bands effective 1 April 2025",
        "figures": ("qualifying_count", "monthly_total", "annual_projection"),
    },
    "provisional": {
        "provision": "Income Tax Act 58/1962 - 4th Schedule, par 19-21 & 27 (estimates, basic amount, "
                     "under-estimation penalty)",
        "rate_source": "SARS Guide to Provisional Tax (IRP6)",
        "figures": ("tax_on_estimate", "first_payment", "second_payment", "total_provisional"),
    },
    "cgt": {
        "provision": "Income Tax Act 58/1962 - 8th Schedule (capital gains) + s26A",
        "rate_source": "SARS CGT inclusion rates + annual exclusion (Budget 2026)",
        "figures": ("net_capital_gain", "taxable_capital_gain", "cgt_payable", "inclusion_rate"),
    },
    "fringe_benefits": {
        "provision": ("Income Tax Act 58/1962 - 7th Schedule (par 7 company car, par 9 accommodation, "
                      "par 11 low-interest loan)"),
        "rate_source": "SARS Guide for Employers in respect of Fringe Benefits",
        "figures": ("company_car", "low_interest_loan", "accommodation", "total_taxable_fringe_benefits"),
    },
    "lump_sum": {
        "provision": "Income Tax Act 58/1962 - 2nd Schedule (retirement / withdrawal lump-sum benefits)",
        "rate_source": "SARS Retirement Lump Sum Benefits tax tables",
        "figures": ("amount", "tax", "net", "effective_rate_pct"),
    },
    "assessed_loss": {
        "provision": "Income Tax Act 58/1962 - s20 (set-off; 80% / R1m cap) & s20A (ring-fencing)",
        "rate_source": "SARS Comprehensive Guide to the ITR14",
        "figures": ("allowed_setoff", "taxable_income_after", "carried_forward"),
    },
    "residency": {
        "provision": "Income Tax Act 58/1962 - s1 'resident' (ordinarily resident + physical-presence test)",
        "rate_source": "SARS Interpretation Note 3 (physical-presence test)",
        "figures": ("status", "resident_by_presence"),
    },
    "exit_tax": {
        "provision": "Income Tax Act 58/1962 - s9H (deemed disposal on ceasing residency) + 8th Schedule",
        "rate_source": "SARS cease-to-be-a-resident guidance",
        "figures": ("deemed_gains", "taxable_capital_gain", "exit_tax_payable"),
    },
    "foreign_income": {
        "provision": "Income Tax Act 58/1962 - s10(1)(o)(ii) (foreign employment income exemption)",
        "rate_source": "SARS Interpretation Note 16 (R1.25m exemption; 183/60-day test)",
        "figures": ("exempt_amount", "taxable_amount", "qualifies"),
    },
}


def _pick_figures(section, keys):
    section = section if isinstance(section, dict) else {}
    return {k: section[k] for k in keys if k in section}


def build_tax_audit_trail(assessment) -> dict:
    """Annotate a tax assessment (assess_all output) with per-section statutory
    provenance + headline figures, so each number is traceable. Pure."""
    assessment = assessment if isinstance(assessment, dict) else {}
    entries = []
    for key, cite in _TAX_CITATIONS.items():
        section = assessment.get(key)
        if not isinstance(section, dict):
            continue
        entries.append({
            "section": key,
            "provision": cite["provision"],
            "rate_source": cite["rate_source"],
            "as_of": section.get("as_of", "SA 2026/27 tax year"),
            "figures": _pick_figures(section, cite["figures"]),
        })
    return {
        "available": bool(entries),
        "as_of": "SA 2026/27 tax year",
        "rates_dated": sa_rates.AS_OF,
        "rates_note": sa_rates.AS_OF_NOTE,
        "entries": entries,
        "count": len(entries),
        "note": ("Every figure above is computed deterministically in code from dated SARS constants - the AI "
                 "does not set any number. Each section cites the statutory provision and the rate source so "
                 "the figure can be reproduced and defended. Re-verify each citation/rate against current SARS "
                 "tables for any year of assessment after 2026/27 (superseded-guidance check)."),
        "disclaimer": "Decision-support / audit-trail only - not tax advice; confirm with a registered tax practitioner.",
    }


def record_tax_audit(analysis_id, assessment) -> dict:
    """Write the tax audit trail to the tamper-evident decision-audit hash chain
    (immutable + reproducible). Returns the record + its chain hash."""
    from services.database import append_audit
    trail = build_tax_audit_trail(assessment)
    record = {
        "analysis_id": str(analysis_id or ""),
        "type": "tax_audit_trail",
        "rates_dated": trail.get("rates_dated"),
        "sections": [e["section"] for e in trail.get("entries", [])],
        "trail": trail,
    }
    res = append_audit(record)
    return {"recorded": True, "sections": record["sections"], **res}
