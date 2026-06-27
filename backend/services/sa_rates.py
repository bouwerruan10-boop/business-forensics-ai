"""
sa_rates.py — single dated source of truth for South African statutory + macro rates.

Update the numbers here when SARB moves rates or the Budget changes a threshold;
every agent that injects sa_rates_block() picks up the change automatically, so no
rate ever has to be hunted down inside a prompt string again.
"""

AS_OF = "2026-06-21"
AS_OF_NOTE = "SARB 28 May 2026 (+25bps) and Budget 2026 (effective 1 April 2026)"

# ── Interest / lending ──
REPO_RATE = 7.00            # %  SARB repo rate
PRIME_RATE = 10.50          # %  prime = repo + 3.5% spread
SARS_INTEREST_RATE = 10.50  # %  interest on outstanding SARS debt (repo + 3.5%)

# ── VAT & turnover-based thresholds (ZAR) ──
VAT_RATE = 15.0
VAT_COMPULSORY_THRESHOLD = 2_300_000   # raised from R1,000,000 on 1 April 2026
VAT_VOLUNTARY_THRESHOLD = 120_000      # raised from R50,000 on 1 April 2026
TURNOVER_TAX_LIMIT = 2_300_000         # micro-business turnover tax ceiling
SBC_GROSS_INCOME_CEILING = 20_000_000  # Section 12E Small Business Corporation

# ── B-BBEE turnover bands (generic codes; some sector codes differ) ──
BBBEE_EME_CEILING = 10_000_000
BBBEE_QSE_CEILING = 50_000_000

# ── SME debt pricing assumptions ──
SME_DEBT_MARGIN_LOW = 3.0   # prime + 3%
SME_DEBT_MARGIN_HIGH = 5.0  # prime + 5%
STRESS_BPS = 200            # +200bps rate-shock stress test


def sme_debt_rate_range():
    """(low, high) all-in SME debt rate = prime + 3% .. prime + 5%."""
    return (PRIME_RATE + SME_DEBT_MARGIN_LOW, PRIME_RATE + SME_DEBT_MARGIN_HIGH)


def sa_rates_block() -> str:
    """Prompt-injectable block of current SA rates/thresholds for any agent."""
    lo, hi = sme_debt_rate_range()
    return (
        "CURRENT SA RATES & STATUTORY THRESHOLDS (as of {asof} - {note}). "
        "Use these exact figures; do NOT substitute remembered values:\n"
        "- SARB repo rate: {repo:.2f}%  |  Prime lending rate: {prime:.2f}%\n"
        "- Typical SME debt pricing: prime + {ml:.0f}-{mh:.0f}% = {lo:.2f}-{hi:.2f}%; "
        "stress-test a +{bps}bps rise\n"
        "- SARS interest on outstanding debt: {sars:.2f}% p.a.\n"
        "- VAT: standard rate {vat:.0f}%; COMPULSORY registration above R{vatc:,.0f} "
        "turnover per 12 months; voluntary from R{vatv:,.0f} (both raised 1 April 2026)\n"
        "- Turnover-tax (micro) ceiling: R{tt:,.0f}; SBC (Section 12E) gross-income "
        "ceiling: R{sbc:,.0f}\n"
        "- B-BBEE: EME below R{eme:,.0f}; QSE R{eme:,.0f}-R{qse:,.0f} turnover"
    ).format(
        asof=AS_OF, note=AS_OF_NOTE, repo=REPO_RATE, prime=PRIME_RATE,
        ml=SME_DEBT_MARGIN_LOW, mh=SME_DEBT_MARGIN_HIGH, lo=lo, hi=hi, bps=STRESS_BPS,
        sars=SARS_INTEREST_RATE, vat=VAT_RATE, vatc=VAT_COMPULSORY_THRESHOLD,
        vatv=VAT_VOLUNTARY_THRESHOLD, tt=TURNOVER_TAX_LIMIT, sbc=SBC_GROSS_INCOME_CEILING,
        eme=BBBEE_EME_CEILING, qse=BBBEE_QSE_CEILING,
    )


# ── Corporate income tax / Small Business Corporation (Section 12E) ──
COMPANY_FLAT_RATE = 27.0          # %  standard company income-tax rate
SBC_TAX_YEAR = "2025/26"          # SBC graduated table below is the 2025/26 year of assessment
# (lower, upper_or_None, marginal_rate, base_tax_at_lower) — verify the current SARS SBC table each year
SBC_BRACKETS = [
    (0,        95_750,   0.00, 0),
    (95_750,   365_000,  0.07, 0),
    (365_000,  550_000,  0.21, 18_848),
    (550_000,  None,     0.27, 57_698),
]


def sbc_tax(taxable_income) -> float:
    """SBC (Section 12E) graduated income tax on taxable income (ZAR)."""
    ti = max(0.0, float(taxable_income or 0))
    for lo, hi, rate, base in SBC_BRACKETS:
        if hi is None or ti <= hi:
            return base + rate * (ti - lo)
    return 0.0


def company_flat_tax(taxable_income) -> float:
    """Flat 27% company income tax on taxable income (ZAR)."""
    return max(0.0, float(taxable_income or 0)) * COMPANY_FLAT_RATE / 100.0


# ── Employment Tax Incentive (ETI) — bands effective 1 April 2025 ──
# Source: ETI Act 26 of 2013 (as amended); SARS "ETI changes with effect from 1 April 2025".
# Monthly incentive per qualifying employee (age 18-29), by monthly remuneration band:
#   R0-2,499.99      : 60% of remuneration (Y1) / 30% (Y2)
#   R2,500-5,499.99  : R1,500 flat (Y1) / R750 (Y2)
#   R5,500-7,499.99  : R1,500 - 75%*(remun-5,500) (Y1) / R750 - 37.5%*(remun-5,500) (Y2)
#   >= R7,500        : nil
ETI_BAND1_CEILING = 2500.0        # R/month; below this the incentive is a % of remuneration
ETI_BAND1_RATE_Y1 = 0.60
ETI_BAND1_RATE_Y2 = 0.30
ETI_BAND2_CEILING = 5500.0        # R/month; flat-amount band up to here
ETI_BAND2_FLAT_Y1 = 1500.0        # R/month, first 12 qualifying months
ETI_BAND2_FLAT_Y2 = 750.0         # R/month, second 12 qualifying months
ETI_TAPER_RATE_Y1 = 0.75          # phase-out per R above R5,500 (Y1)
ETI_TAPER_RATE_Y2 = 0.375         # phase-out per R above R5,500 (Y2)
ETI_EARN_CEILING = 7500.0         # R/month; employees earning >= this do not qualify
ETI_MAX_MONTHLY_Y1 = 1500.0       # overall max monthly incentive, first 12 months
ETI_MAX_MONTHLY_Y2 = 750.0        # overall max monthly incentive, second 12 months
ETI_AGE_MIN = 18
ETI_AGE_MAX = 29

# ── Skills Development Levy ──
SDL_RATE = 1.0                    # %  of total annual payroll
SDL_EXEMPT_PAYROLL = 500_000      # R/year; below this the employer is SDL-exempt
