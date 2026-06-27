"""
lump_sum.py - deterministic SA retirement / severance / withdrawal lump-sum tax.

Pure functions; the LLM only narrates. Lump sums are taxed OUTSIDE the normal
tables, on a CUMULATIVE lifetime basis: the tax on a new lump sum is the tax on
(all prior lump sums + this one) less the tax on the prior lump sums. Two tables:
- the retirement / severance / death table (R550,000 tax-free), and
- the pre-retirement WITHDRAWAL table (R27,500 tax-free).
Re-verify the tables against the SARS Retirement Lump Sum Benefits rates page
each year (no change for 2026).
"""

# (lower_threshold, marginal_rate, cumulative_tax_at_lower) — retirement/severance
RETIREMENT_TABLE = [
    (0, 0.0, 0),
    (550_000, 0.18, 0),
    (770_000, 0.27, 39_600),
    (1_155_000, 0.36, 143_550),
]
# pre-retirement withdrawal
WITHDRAWAL_TABLE = [
    (0, 0.0, 0),
    (27_500, 0.18, 0),
    (726_000, 0.27, 125_730),
    (1_089_000, 0.36, 223_740),
]


def _num(x):
    try:
        v = float(x or 0)
    except (TypeError, ValueError):
        return 0.0
    return v if v > 0 else 0.0


def _table_tax(amount, table):
    a = _num(amount)
    lower, rate, base = table[0]
    for lo, r, b in table:
        if a >= lo:
            lower, rate, base = lo, r, b
        else:
            break
    return base + rate * (a - lower)


def _cumulative(amount, prior, table):
    """Tax on this lump = table(prior + amount) - table(prior)."""
    a, p = _num(amount), _num(prior)
    return round(max(0.0, _table_tax(p + a, table) - _table_tax(p, table)), 2)


def retirement_lump_sum_tax(amount, prior_lump_sums=0):
    """Tax on a retirement (or death) fund lump sum (R550k tax-free, cumulative)."""
    return _cumulative(amount, prior_lump_sums, RETIREMENT_TABLE)


def severance_benefit_tax(amount, prior_lump_sums=0):
    """Severance benefits use the same table as retirement lump sums."""
    return _cumulative(amount, prior_lump_sums, RETIREMENT_TABLE)


def withdrawal_lump_sum_tax(amount, prior_withdrawals=0):
    """Tax on a pre-retirement withdrawal (R27,500 tax-free, cumulative)."""
    return _cumulative(amount, prior_withdrawals, WITHDRAWAL_TABLE)


def assess_lump_sum(amount, kind="retirement", prior=0):
    """Assess a single lump sum. kind: retirement | severance | withdrawal."""
    a = _num(amount)
    if kind == "withdrawal":
        tax = withdrawal_lump_sum_tax(a, prior)
    else:
        tax = retirement_lump_sum_tax(a, prior)   # retirement + severance share the table
    return {
        "as_of": "SA 2026/27 tax year",
        "kind": kind if kind in ("retirement", "severance", "withdrawal") else "retirement",
        "amount": round(a, 2),
        "prior_lump_sums": round(_num(prior), 2),
        "tax": tax,
        "net": round(a - tax, 2),
        "effective_rate_pct": round(tax / a * 100, 2) if a > 0 else 0.0,
        "disclaimer": "Decision-support only - not tax advice; confirm with a tax practitioner. "
                      "Lump-sum tax is cumulative over your lifetime - SARS aggregates all prior lump sums.",
    }
