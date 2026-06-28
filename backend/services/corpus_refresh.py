"""Audited changelog of dated-corpus refreshes — the 'research proposes, human approves' record.

Each refresh lists what changed (from -> to) with its authoritative source, so a corpus update
is never silent. Pairs with corpus_currency.py (the freshness DETECTOR): the detector flags
staleness, this records what was done about it. Surfaced at GET /api/admin/corpus-refresh.
"""

REFRESHES = [
    {
        "date": "2026-06-28",
        "corpus": "SA interest rates (sa_rates.py)",
        "from_tax_year": "2026/27",
        "to_tax_year": "2026/27",
        "applied": True,
        "sources": [
            "SARS Interest Rate Table 3 (Legal-Pub-IRT-03) — official rate of interest, fringe-benefit loans",
            "SARS Interest Rate Table 1 (Legal-Pub-IRT-01) — interest on outstanding taxes",
            "Confirmed directly from the SARS PDF tables (sars.gov.za/legal-counsel/.../tables-of-interest-rates/)",
        ],
        "changes": [
            {"field": "official_rate_of_interest", "from": 7.75, "to": 8.00},   # eff. 1 Jun 2026 (repo 7.00 + 1%)
            {"field": "sars_interest_rate", "from": 10.50, "to": 10.25},        # eff. 1 Mar 2026
        ],
        "unchanged": [
            "REPO_RATE 7.00 / PRIME_RATE 10.50 (the +25bps already applied)",
            "All Budget-2026 figures (rebates, brackets, VAT/CGT thresholds) refreshed 2026-06-24 below",
        ],
        "note": ("Flagged by the SARS rate-currency checker (services/sars_rate_check.py) as drift, then "
                 "CONFIRMED against the authoritative SARS Interest Rate PDFs before applying. The official "
                 "rate moved 7.75%->8.00% on 1 Jun 2026 (it had lagged the repo rate, which sa_rates already "
                 "carried at 7.00%); outstanding-tax interest moved 10.50%->10.25% on 1 Mar 2026. The checker "
                 "proposed; a human verified the source; the change is recorded here."),
    },
    {
        "date": "2026-06-24",
        "corpus": "SA personal income tax (relocation_tax / tax engine + stay-and-optimise levers)",
        "from_tax_year": "2025/26",
        "to_tax_year": "2026/27",
        "applied": True,
        "sources": [
            "SARS Budget 2026 Tax Guide (treasury.gov.za / sars.gov.za)",
            "KPMG SA Budget Guide 2026/27",
            "PKF / PwC SA Tax Guide 2026/27",
            "TaxTim / Werksmans Budget 2026 summaries",
        ],
        "changes": [
            {"field": "primary_rebate", "from": 17235, "to": 17820},
            {"field": "secondary_rebate_65", "from": 9444, "to": 9765},
            {"field": "tertiary_rebate_75", "from": 3145, "to": 3249},
            {"field": "medical_credit_main_monthly", "from": 364, "to": 376},
            {"field": "medical_credit_addl_monthly", "from": 246, "to": 254},
            {"field": "retirement_deduction_cap_s11F", "from": 350000, "to": 430000},
            {"field": "cgt_annual_exclusion", "from": 40000, "to": 50000},
            {"field": "primary_residence_cgt_exclusion", "from": 2000000, "to": 3000000},
            {"field": "sbc_zero_rate_band_s12E", "from": 95750, "to": 99000},
            {"field": "pit_bracket_upper_bounds",
             "from": [237100, 370500, 512800, 673000, 857900, 1817000],
             "to": [245100, 383100, 530200, 695800, 887000, 1878600]},
        ],
        "unchanged": [
            "Interest exemption (R23,800 / R34,500 at 65+)",
            "TFSA (R36,000/yr, R500,000 lifetime)",
            "CGT inclusion 40% / max ~18% effective",
            "Dividends withholding 20% (final)",
            "PIT marginal rates (18/26/31/36/39/41/45)",
        ],
        "note": ("All adjustments ~3.4% inflation (Budget 2026, tabled Feb 2026). Cross-checked across "
                 "SARS's own Budget Tax Guide and the Big-4/PKF guides before applying. The SBC full "
                 "graduated table beyond the 0% band should be re-confirmed if SBC reporting deepens."),
    },
]


def corpus_refresh_log():
    """Audited record of corpus refreshes (what changed, from->to, sourced)."""
    return {
        "refreshes": REFRESHES,
        "count": len(REFRESHES),
        "note": ("Changelog of dated-corpus refreshes - research proposes, a human approves, and the "
                 "change is recorded here with its source. Pairs with /api/admin/corpus-currency "
                 "(the freshness detector). The numbers themselves live in code, never auto-written."),
    }
