"""
cgt.py - deterministic SA Capital Gains Tax (8th Schedule).

Pure functions; the LLM only narrates. Inclusion rates, exclusions and the
trust rate come from the dated `sa_rates`. CGT is not a separate tax: the
taxable capital gain is added to taxable income and taxed at the taxpayer's
rate (marginal for individuals, 27% company, 45% ordinary trust). The exit-tax
(s9H) engine reuses these functions. Re-verify figures against SARS each year.

Mechanics:
  aggregate gain = sum(gains) - primary-residence exclusion - sum(losses)
  net capital gain = aggregate gain - annual exclusion (individuals only)
  taxable capital gain = net capital gain x inclusion rate (40% / 80%)
  CGT = tax on (other income + taxable capital gain) - tax on other income
"""

from services import sa_rates
from services.income_tax import income_tax, _num


def aggregate_capital_gain(total_gains, total_losses=0, primary_residence_gain=0):
    """Sum of gains, less the primary-residence exclusion (first R3m of that gain)
    and capital losses. May be negative (an assessed capital loss)."""
    pr_excl = min(_num(primary_residence_gain), sa_rates.CGT_PRIMARY_RESIDENCE_EXCLUSION)
    return _num(total_gains) - pr_excl - _num(total_losses)


def net_capital_gain(total_gains, total_losses=0, taxpayer="individual",
                     primary_residence_gain=0, year_of_death=False):
    """Aggregate gain less the individual annual (or death) exclusion. Floored at 0
    (a net capital loss is carried forward, not taxed)."""
    net = aggregate_capital_gain(total_gains, total_losses, primary_residence_gain)
    if net <= 0:
        return 0.0
    if taxpayer == "individual":
        excl = sa_rates.CGT_DEATH_EXCLUSION if year_of_death else sa_rates.CGT_ANNUAL_EXCLUSION
        net = max(0.0, net - excl)
    return round(net, 2)


def taxable_capital_gain(total_gains, total_losses=0, taxpayer="individual",
                         primary_residence_gain=0, year_of_death=False):
    """Net capital gain x the inclusion rate (the amount added to taxable income)."""
    ncg = net_capital_gain(total_gains, total_losses, taxpayer, primary_residence_gain, year_of_death)
    incl = (sa_rates.CGT_INCLUSION_COMPANY if taxpayer in ("company", "trust")
            else sa_rates.CGT_INCLUSION_INDIVIDUAL)
    return round(ncg * incl, 2)


def assess_cgt(total_gains, total_losses=0, taxpayer="individual",
               primary_residence_gain=0, year_of_death=False,
               other_taxable_income=0, age=0):
    """Full CGT assessment. For individuals the gain is taxed at the marginal rate
    (incremental over other income); company 27%, ordinary trust 45%."""
    tcg = taxable_capital_gain(total_gains, total_losses, taxpayer, primary_residence_gain, year_of_death)
    ncg = net_capital_gain(total_gains, total_losses, taxpayer, primary_residence_gain, year_of_death)

    if taxpayer == "company":
        cgt = tcg * sa_rates.COMPANY_FLAT_RATE / 100.0
    elif taxpayer == "trust":
        cgt = tcg * sa_rates.TRUST_FLAT_RATE / 100.0
    else:
        base = _num(other_taxable_income)
        cgt = income_tax(base + tcg, age) - income_tax(base, age)

    cgt = round(max(0.0, cgt), 2)
    gross = _num(total_gains)
    return {
        "as_of": "SA 2026/27 tax year",
        "taxpayer": taxpayer if taxpayer in ("individual", "company", "trust") else "individual",
        "aggregate_capital_gain": round(aggregate_capital_gain(total_gains, total_losses, primary_residence_gain), 2),
        "net_capital_gain": ncg,
        "inclusion_rate": (sa_rates.CGT_INCLUSION_COMPANY if taxpayer in ("company", "trust")
                           else sa_rates.CGT_INCLUSION_INDIVIDUAL),
        "taxable_capital_gain": tcg,
        "cgt_payable": cgt,
        "effective_rate_pct": round(cgt / gross * 100, 2) if gross > 0 else 0.0,
        "disclaimer": "Decision-support only - not tax advice; confirm with a tax practitioner.",
    }
