"""Relocation & cross-border tax-residency FIRST-PASS — the "Tax Me If You Can" engine (P1).

DECISION-SUPPORT / FACTUAL LANDSCAPE ONLY — NOT tax, legal, or financial advice.

Design invariants (non-negotiable):
  * Deterministic — every rule/figure comes from the DATED, SOURCED corpus below. No LLM in
    the numbers (Imara's deterministic-first DNA).
  * It INFORMS and routes to a licensed advisor; it does NOT design or market a specific
    cross-border arrangement (doing so is a reportable DAC6/MDR "intermediary" act).
  * Legal relocation + tax efficiency ONLY — never evasion. Substance (GAAR) and CRS
    transparency are surfaced on every result so the user understands you cannot "hide" or
    fake a move.
  * Indicative + dated; tax law changes yearly — re-verify AS_OF before relying.
"""

AS_OF = "2026-06"  # corpus date — rules change yearly; re-verify before relying.
FX_AS_OF = "Jun 2026 (indicative)"
ZAR_PER_EUR = 20.0   # indicative, dated — flat-fee regimes are quoted in EUR/CHF
ZAR_PER_CHF = 21.0

INCOME_TYPES = ("employment", "business", "dividends", "interest", "rental", "capital_gains", "pension")

# ── Indicative tax quantification (SA 2025/26; sourced) ────────────────────────
# INDICATIVE ONLY — headline/effective rates, NOT a computation of actual liability.
TAX_AS_OF = "SA 2025/26 tax year"
SA_EFFICIENCY_AS_OF = "SA 2025/26"
SA_BRACKETS = [(237100, 0.18), (370500, 0.26), (512800, 0.31), (673000, 0.36),
               (857900, 0.39), (1817000, 0.41), (float("inf"), 0.45)]
SA_PRIMARY_REBATE = 17235     # 2025/26 primary rebate
SA_DIV_WHT = 0.20             # dividends withholding (final)
SA_CGT_EFFECTIVE = 0.18       # individual max effective CGT (40% inclusion x 45%)
SA_SECONDARY_REBATE = 9444    # additional age-65+ rebate (2025/26, unchanged from 2024/25)
SA_TERTIARY_REBATE = 3145     # additional age-75+ rebate
SA_INTEREST_EXEMPT_U65 = 23800   # annual local-interest exemption, under 65
SA_INTEREST_EXEMPT_65 = 34500    # annual local-interest exemption, 65+
SA_CGT_ANNUAL_EXCL = 40000       # annual capital-gain exclusion
SA_RA_CAP = 350000               # s11F retirement-contribution deduction cap
MEDICAL_CREDIT_MAIN = 364        # s6A monthly credit, member + first dependant
MEDICAL_CREDIT_ADDL = 246        # s6A monthly credit, each further dependant


def _num(v):
    """Coerce arbitrary input to a non-negative, FINITE float; junk/nan/inf -> 0.0."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    import math as _m
    return f if (f > 0 and _m.isfinite(f)) else 0.0


def _sa_income_tax(taxable):
    """SA progressive PIT on ordinary income (2025/26 brackets, less primary rebate)."""
    taxable = _num(taxable)
    tax, lower = 0.0, 0.0
    for upper, rate in SA_BRACKETS:
        if taxable <= lower:
            break
        tax += (min(taxable, upper) - lower) * rate
        lower = upper
    return max(0.0, tax - SA_PRIMARY_REBATE)


def _sa_current_tax(income, age=0, deductions=None):
    """Indicative current SA personal tax, refined by AGE (age rebates + age-tiered interest
    exemption) and EXISTING deductions already claimed (retirement contribution, s18A donations,
    medical-scheme members). Applies the annual interest + capital-gain exclusions so the
    baseline is net rather than gross. Still indicative."""
    age = int(_num(age))
    d = deductions if isinstance(deductions, dict) else {}
    interest = _num(income.get("interest"))
    ordinary = sum(_num(income.get(k)) for k in ("employment", "business", "interest", "rental", "pension"))
    int_exempt = min(interest, SA_INTEREST_EXEMPT_65 if age >= 65 else SA_INTEREST_EXEMPT_U65)
    ra = min(_num(d.get("retirement_contribution")), SA_RA_CAP, 0.275 * ordinary)
    don = min(_num(d.get("donations")), 0.10 * ordinary)
    taxable_ordinary = max(0.0, ordinary - int_exempt - ra - don)
    tax = _sa_income_tax(taxable_ordinary)           # already net of the primary rebate
    if age >= 65:
        tax = max(0.0, tax - SA_SECONDARY_REBATE)
    if age >= 75:
        tax = max(0.0, tax - SA_TERTIARY_REBATE)
    members = int(_num(d.get("medical_members")))
    if members > 0:
        credit = (MEDICAL_CREDIT_MAIN * min(members, 2) + MEDICAL_CREDIT_ADDL * max(0, members - 2)) * 12
        tax = max(0.0, tax - credit)
    cg = max(0.0, _num(income.get("capital_gains")) - SA_CGT_ANNUAL_EXCL)
    return tax + _num(income.get("dividends")) * SA_DIV_WHT + cg * SA_CGT_EFFECTIVE


def _dest_tax(income, rates):
    """Indicative destination personal tax = sum(amount x per-type effective rate)."""
    return sum(_num(income.get(k)) * rates.get(k, 0.0) for k in INCOME_TYPES)

# ── Origin: South Africa — cessation of tax residence ──────────────────────────
SA_EXIT = {
    "jurisdiction": "South Africa",
    "code": "ZA",
    "residency_tests": [
        "Ordinarily resident (a facts-and-circumstances test of your real home/intention), or",
        "Physical-presence test — broadly >91 days/yr over 6 years; you CEASE on this basis only after 330 continuous full days outside SA.",
    ],
    "exit_charge": (
        "Section 9H 'exit charge': ceasing SA tax residency triggers a DEEMED DISPOSAL of your "
        "worldwide assets at market value (a capital-gains event) on the day before cessation — "
        "EXCLUDING SA immovable property (and a few categories). Budget for the CGT before you move."
    ),
    "process": [
        "Formally notify SARS via the RAV01 on eFiling (capture the cessation date) and obtain the non-residency confirmation letter — merely leaving SA does NOT end tax residency.",
        "Retirement-fund withdrawal has a 3-year-after-cessation lock nuance.",
    ],
    "sources": ["SARS (cease-to-be-a-resident)", "PKF SA 2025", "Tax Consulting SA"],
}

# ── Destination corpus (legal regimes) ─────────────────────────────────────────
DESTINATIONS = {
    "AE": {
        "name": "United Arab Emirates",
        "residency_test": "183 days in a 12-month period (or 90 days + a home/ties, for citizens/residents). A Tax Residency Certificate now requires real substance.",
        "headline": "0% personal income tax; 9% corporate tax on business profit above AED 375,000 (0% below; qualifying free-zone income can be 0%).",
        "income_treatment": {
            "employment": "0% personal tax.",
            "business": "personal 0%, but company profit over AED 375k taxed at 9% (substance + free-zone rules matter).",
            "dividends": "0% personal tax on dividends received.",
            "interest": "0% personal tax.",
            "rental": "0% personal tax (UAE-source rental may have local fees).",
            "capital_gains": "0% personal CGT.",
            "pension": "0% personal tax.",
        },
        "gotchas": ["Real substance required for a TRC (a mailbox won't pass).", "9% corporate tax applies to active UAE business profit.", "Your HOME country's exit/CFC rules still apply on the way out."],
        "effective_rates": {"employment": 0.0, "business": 0.0, "dividends": 0.0, "interest": 0.0, "rental": 0.0, "capital_gains": 0.0, "pension": 0.0},
        "sources": ["PwC Tax Summaries (UAE)", "Chambers Corporate Tax 2025 (UAE)"],
    },
    "CY": {
        "name": "Cyprus (non-domiciled)",
        "residency_test": "183 days, OR the 60-day rule (a permanent home + business/employment ties in Cyprus and not tax-resident elsewhere on the day-count).",
        "headline": "Non-domiciled residents: 0% Special Defence Contribution on dividends, interest and rental for up to 17 years (effective ~5% with the GHS health levy, which is capped).",
        "income_treatment": {
            "employment": "taxed on the normal PIT scale (0%–35%); a 50% exemption may apply to high earners — check current thresholds.",
            "business": "12.5% corporate tax on a Cyprus company; salary on the PIT scale.",
            "dividends": "0% SDC under non-dom (the headline benefit) for up to 17 years.",
            "interest": "0% SDC under non-dom for up to 17 years.",
            "rental": "0% SDC on foreign rental under non-dom; PIT may still apply to net rental.",
            "capital_gains": "CGT generally only on Cyprus-situated immovable property; other gains usually outside CGT.",
            "pension": "foreign pensions: choose 5% flat above a small exemption, or the normal scale.",
        },
        "gotchas": ["The big win is for PASSIVE income (dividends/interest); salaries still hit the PIT scale.", "Non-dom lasts 17 years (extendable from 2026 at €250k per 5-year block).", "EU member — DAC6 applies to any reportable arrangement."],
        "effective_rates": {"employment": 0.20, "business": 0.125, "dividends": 0.0, "interest": 0.0, "rental": 0.0, "capital_gains": 0.0, "pension": 0.05},
        "sources": ["Cyprus Tax Life 2026", "Mondaq (60-day rule)", "Harneys"],
    },
    "PT": {
        "name": "Portugal (IFICI / 'NHR 2.0')",
        "residency_test": "183 days, or a permanent home in Portugal on 31 Dec.",
        "headline": "IFICI (replaced NHR on 1 Jan 2025): 20% flat on ELIGIBLE Portuguese professional income + exemption on most foreign income — but eligibility is narrow.",
        "income_treatment": {
            "employment": "20% flat ONLY if in a qualifying high-value/innovation role; otherwise the normal scale up to 48%.",
            "business": "20% flat only for qualifying activities; otherwise normal rates.",
            "dividends": "foreign dividends generally exempt under IFICI (declared for rate progression).",
            "interest": "foreign interest generally exempt under IFICI.",
            "rental": "foreign rental generally exempt under IFICI; PT-source rental taxed.",
            "capital_gains": "foreign capital gains generally exempt under IFICI (rules vary by asset).",
            "pension": "EXCLUDED — foreign pensions are NOT covered by IFICI (a key change from old NHR).",
        },
        "gotchas": ["Eligibility is NARROW: highly-qualified innovation/R&D/science/tech/health roles, a degree (EQF level 6+), and no PT residence in the prior 5 years.", "Pensions are excluded entirely.", "10-year validity. EU member — DAC6 applies."],
        "effective_rates": {"employment": 0.20, "business": 0.20, "dividends": 0.0, "interest": 0.0, "rental": 0.0, "capital_gains": 0.0, "pension": 0.35},
        "sources": ["Global Citizen Solutions (IFICI 2026)", "IBA overview", "immigrantinvest"],
    },
    "MU": {
        "name": "Mauritius",
        "residency_test": "183 days in the tax year, OR 270 days across the current plus two preceding years.",
        "headline": "Remittance basis on foreign income (taxed only if brought INTO Mauritius), NO capital gains / inheritance / wealth tax, and a simplified 0%-20% income tax scale (2025). Popular SA corridor with a SA double-tax treaty.",
        "income_treatment": {
            "employment": "Mauritius-source employment on the 2025 scale: 0% to MUR 500k, 10% to MUR 1m, 20% above MUR 1m.",
            "business": "15% corporate tax; an 80% partial exemption can lower the effective rate on qualifying foreign-source company income.",
            "dividends": "foreign dividends taxed ONLY if remitted to Mauritius; 0% if kept offshore.",
            "interest": "foreign interest taxed only if remitted; 0% if kept offshore.",
            "rental": "foreign rental taxed only if remitted; Mauritius-source rental on the scale.",
            "capital_gains": "0% - Mauritius levies no capital gains tax.",
            "pension": "foreign pension taxed only if remitted; 0% if kept offshore.",
        },
        "gotchas": ["Remittance basis means money you BRING IN is taxable up to 20% - plan cash-flow, not just headline residency.", "A solidarity levy can apply to high earners (income above ~MUR 3m) - confirm the current rate.", "SA double-tax treaty exists, but SA s9H exit tax, substance and CRS still apply."],
        "effective_rates": {"employment": 0.20, "business": 0.15, "dividends": 0.0, "interest": 0.0, "rental": 0.0, "capital_gains": 0.0, "pension": 0.0},
        "sources": ["PwC Tax Summaries (Mauritius)", "Mauritius Revenue Authority", "Mauritius Finance Act 2025"],
    },
    "MT": {
        "name": "Malta (non-domiciled)",
        "residency_test": "183 days, or otherwise making Malta your ordinary residence.",
        "headline": "Non-dom remittance basis: foreign income taxed only if remitted to Malta, and foreign capital gains are NOT taxed even if remitted. A EUR 5,000 minimum tax applies if unremitted foreign income is >= EUR 35,000.",
        "income_treatment": {
            "employment": "Malta-source employment on the progressive scale (up to 35%).",
            "business": "the full-imputation system can give a ~5% effective corporate rate via the 6/7 shareholder refund - needs proper structuring.",
            "dividends": "foreign dividends taxed only if remitted to Malta; 0% if kept offshore.",
            "interest": "foreign interest taxed only if remitted; 0% if kept offshore.",
            "rental": "foreign rental taxed only if remitted to Malta.",
            "capital_gains": "foreign capital gains are NOT taxed in Malta even if remitted (a key advantage).",
            "pension": "foreign pension taxed only if remitted; the GRP/MRP programmes offer a flat 15% on remitted foreign income.",
        },
        "gotchas": ["EUR 5,000 minimum tax once unremitted foreign income reaches EUR 35,000 (per couple).", "The Global/Malta Residence Programmes give a flat 15% on remitted foreign income but carry a EUR 15,000 minimum tax.", "EU member - DAC6 applies; substance and CRS still apply."],
        "effective_rates": {"employment": 0.35, "business": 0.05, "dividends": 0.0, "interest": 0.0, "rental": 0.0, "capital_gains": 0.0, "pension": 0.0},
        "sources": ["PwC Tax Summaries (Malta)", "Malta Commissioner for Tax and Customs", "Trident Trust non-dom key facts"],
    },
    "GR": {
        "name": "Greece (non-dom EUR 100k flat / 7% pension)",
        "residency_test": "183 days; the EUR 100k HNWI regime needs you to NOT have been GR-tax-resident in 7 of the last 8 years (5 of last 6 for the pension regime).",
        "headline": "A FIXED EUR 100,000/yr fee on ALL foreign income (HNWI non-dom, 15 yrs, needs a EUR 500k investment) - worth it ONLY for very high earners; SEPARATELY, a 7% flat on foreign PENSIONS for retirees.",
        "income_treatment": {
            "employment": "foreign employment covered by the EUR 100k flat fee; GR-source income on the normal scale up to 44%.",
            "business": "foreign business income covered by the flat fee; GR-source taxed normally.",
            "dividends": "foreign dividends covered by the EUR 100k flat fee (no extra tax).",
            "interest": "foreign interest covered by the flat fee.",
            "rental": "foreign rental covered by the flat fee; GR-source rental taxed.",
            "capital_gains": "foreign capital gains covered by the flat fee.",
            "pension": "the SEPARATE regime: 7% flat on foreign pension - far cheaper than the EUR 100k fee for retirees.",
        },
        "gotchas": ["The EUR 100k regime only beats SA tax once your SA bill exceeds ~R2m (very high income).", "Pensioners should use the separate 7% foreign-pension regime instead.", "Needs a EUR 500k investment for the HNWI regime; EU member - DAC6 applies."],
        "flat_fee_zar": 2000000, "flat_fee_local": "EUR 100,000/yr",
        "flat_fee_note": "Fixed EUR 100k/yr on all foreign income (HNWI non-dom) ~= R2.0m at ~R20/EUR, regardless of income - so it only saves money above ~R2m of current SA tax. The 7% pension regime is a separate, far cheaper option for retirees.",
        "sources": ["Astons (Greek non-dom 2025)", "PwC Tax Summaries (Greece)", "Grant Thornton GR 2025 reform"],
    },
    "IT": {
        "name": "Italy (EUR 200k/300k flat / 7% pension)",
        "residency_test": "Italian tax residence; the flat regime needs no IT residence in 9 of the last 10 years.",
        "headline": "A FIXED annual fee on all foreign income - RAISED to EUR 300,000/yr for new residents from 1 Jan 2026 (EUR 200k for 2025 entrants; EUR 100k grandfathered pre-Aug-2024). SEPARATELY, a 7% flat on foreign pension for retirees in small Southern-Italy towns.",
        "income_treatment": {
            "employment": "foreign income covered by the flat fee; IT-source income on the normal scale up to 43%.",
            "business": "foreign business income covered by the flat fee.",
            "dividends": "foreign dividends covered by the flat fee.",
            "interest": "foreign interest covered by the flat fee.",
            "rental": "foreign rental covered by the flat fee.",
            "capital_gains": "foreign capital gains covered (a substantial-shareholding exclusion can apply in the first years).",
            "pension": "the SEPARATE regime: 7% flat on foreign pension for retirees settling in a <20,000-population town in Southern Italy (Sicily/Calabria/Puglia/etc.), 10 yrs.",
        },
        "gotchas": ["At EUR 300k/yr (2026) the flat regime only beats SA tax above roughly R14m income - very niche.", "The 7% Southern-Italy pension regime is the accessible route for retirees.", "EU member - DAC6 applies."],
        "flat_fee_zar": 6000000, "flat_fee_local": "EUR 300,000/yr (2026 new entrants)",
        "flat_fee_note": "Fixed fee on all foreign income, raised to EUR 300k/yr from 1 Jan 2026 for new residents (~R6.0m at ~R20/EUR). Ultra-high-income only. The 7% Southern-Italy pension regime is separate and far cheaper.",
        "sources": ["PwC Tax Summaries (Italy)", "Agenzia delle Entrate (new-residents regime)", "Italy Budget Law 2026"],
    },
    "CH": {
        "name": "Switzerland (lump-sum / forfait)",
        "residency_test": "Swiss tax domicile; available only to foreigners NOT gainfully employed in Switzerland who are new (or 10+ years absent).",
        "headline": "Expenditure-based 'lump-sum' (forfait) tax: a minimum federal taxable base of CHF 434,700 taxed at ordinary cantonal rates - a fixed, canton-negotiated annual bill (often ~CHF 130k-200k) regardless of actual worldwide income.",
        "income_treatment": {
            "employment": "you may NOT be gainfully employed in CH; foreign employment is covered by the lump-sum base.",
            "business": "no Swiss gainful activity permitted under the regime.",
            "dividends": "covered by the lump-sum base (not taxed separately on the expenditure basis).",
            "interest": "covered by the lump-sum base.",
            "rental": "covered by the lump-sum base (Swiss-situated property can raise the base).",
            "capital_gains": "private capital gains are generally tax-free in Switzerland.",
            "pension": "covered by the lump-sum base.",
        },
        "gotchas": ["Only worth it for the very wealthy; some cantons (e.g. Zurich) have ABOLISHED it.", "You may NOT work in Switzerland.", "The base + cost of living are high; the deal is negotiated per canton (Ticino/Vaud favourable)."],
        "flat_fee_zar": 3150000, "flat_fee_local": "~CHF 150,000/yr (indicative; canton-dependent)",
        "flat_fee_note": "Forfait min federal base CHF 434,700 taxed at cantonal rates -> indicative tax ~CHF 150k (~R3.15m at ~R21/CHF). Canton-negotiated; no gainful Swiss activity allowed.",
        "sources": ["KPMG CH (lump-sum 2025)", "Swiss Federal Dept of Finance", "PwC Tax Summaries (Switzerland)"],
    },
}

# Residency / investment-route / substance enrichment per corridor (all have a SA double-tax treaty).
_ENRICH = {
    "AE": {"regime": "rate", "dta_with_sa": True,
           "investment_route": "UAE Golden Visa via ~AED 2m property (or ~AED 500k entrepreneur route); 10-yr renewable.",
           "substance": "Real presence for a Tax Residency Certificate (a mailbox won't pass); 9% corporate tax on active UAE business profit."},
    "CY": {"regime": "rate", "dta_with_sa": True,
           "investment_route": "Cyprus permanent residence ~EUR 300k property, or the 60-day rule with a home + ties.",
           "substance": "Permanent home + genuine ties; maintain non-dom status (17-yr clock)."},
    "PT": {"regime": "rate", "dta_with_sa": True,
           "investment_route": "Portugal Golden Visa ~EUR 500k qualifying funds/VC (real-estate route removed 2023/25) or EUR 250k cultural donation; D7 passive-income visa for retirees.",
           "substance": "183 days or a PT home on 31 Dec; IFICI eligibility is narrow (qualifying role + degree + no PT residence 5 yrs)."},
    "MU": {"regime": "rate", "dta_with_sa": True,
           "investment_route": "Mauritius residence via ~US$375k property (PDS/IRS/RES) or the Premium / Occupation-permit route.",
           "substance": "183 days (or 270 over 3 yrs); remittance basis - plan what you bring in."},
    "MT": {"regime": "rate", "dta_with_sa": True,
           "investment_route": "Malta residence ~EUR 375k owned property (or ~EUR 14k/yr rent) + ~EUR 60k admin/contribution fees.",
           "substance": "Ordinary residence; non-dom; EUR 5k (or EUR 15k GRP/MRP) minimum tax."},
    "GR": {"regime": "flat_fee", "dta_with_sa": True,
           "investment_route": "Greece Golden Visa EUR 250k-800k property (EUR 800k Athens/Thessaloniki/islands); the EUR 100k regime additionally needs a EUR 500k investment.",
           "substance": "183+ days; genuine Greek residence; HNWI non-dom clock (not GR-resident 7 of last 8 yrs)."},
    "IT": {"regime": "flat_fee", "dta_with_sa": True,
           "investment_route": "Italy investor visa EUR 250k (innovative startup) / EUR 500k (company) / EUR 2m (govt bonds), or ordinary residence.",
           "substance": "Genuine Italian residence; flat regime needs no IT residence in 9 of last 10 yrs."},
    "CH": {"regime": "flat_fee", "dta_with_sa": True,
           "investment_route": "Residence permit tied to the canton-negotiated lump-sum arrangement; no fixed investment but a high living-cost commitment.",
           "substance": "Genuine domicile in the chosen canton; no gainful Swiss activity."},
}

GUARDRAILS = [
    {"title": "Exit tax first", "detail": "Leaving your current country can trigger an exit/deemed-disposal CGT (e.g. SA s9H) before you arrive anywhere. Model the cost of LEAVING, not just the destination rate."},
    {"title": "Substance over form (GAAR)", "detail": "You must GENUINELY relocate — real home, real days, real ties. A sham move, a mailbox, or round-tripping fails anti-avoidance rules (GAAR) and can carry promoter/penalty exposure."},
    {"title": "Transparency is the default (CRS)", "detail": "Under the CRS your financial accounts are reported automatically between countries (CARF extends this to crypto). This is about LEGAL relocation, not hiding income — assume everything is visible to tax authorities."},
    {"title": "This is information, not an arrangement (DAC6/MDR)", "detail": "Designing or marketing a reportable cross-border tax arrangement makes the designer an 'intermediary' with disclosure duties and penalties. This tool gives you the factual landscape; it does not design or recommend a specific arrangement."},
    {"title": "Use a licensed advisor", "detail": "Only a licensed cross-border tax advisor / attorney (with professional-indemnity insurance) may ADVISE on or implement any of this. Treat this first-pass as preparation for that conversation, not a substitute for it."},
    {"title": "Keep a company? Model the company, not just you (CFC)", "detail": "If you relocate but keep a >50%-SA-owned foreign company, SA's controlled-foreign-company rules (s9D) can attribute its net income back to you while you remain a resident; and an SA company you keep stays SA-taxed. Relocating the person without restructuring the business often does NOT achieve the saving - model the company too, with a licensed advisor."},
]

# Compliant order-of-operations (preparation, not an instruction to act).
SEQUENCING = [
    "Decide you GENUINELY intend to relocate - real home, real days, real ties (substance), not a paper move.",
    "Plan the SA exit: ceasing SA tax residency triggers the s9H deemed-disposal exit CGT - model and time it.",
    "Cease SA tax residency correctly (the 330-day physical-presence route or a DTA tie-breaker) and file the SARS RAV01 + obtain a tax-clearance.",
    "Establish genuine residency + substance in the destination (days, a home, ties, and a Tax Residency Certificate where needed).",
    "Address any company or trust you keep - SA CFC (s9D) and SA-company tax may still apply; restructure with advice.",
    "Stay transparent: CRS/CARF report your accounts automatically; for EU destinations a designed arrangement can be reportable under DAC6/MDR.",
    "Engage a LICENSED cross-border tax advisor + immigration agent (with PI insurance) to review, sign off and execute - this tool is preparation, not a substitute.",
]

COST_CONSIDERATIONS = [
    "Residency / golden-visa investment threshold (varies widely - see each corridor's investment_route).",
    "Cross-border tax + immigration advisory fees (commonly R100k-R500k+ to set up correctly).",
    "Ongoing substance + cost-of-living in the destination (real days, a real home).",
    "The SA exit CGT (s9H) - a one-off cost of LEAVING, before any destination saving.",
    "Double-tax-treaty relief: SA has a DTA with every corridor here, which governs the residence tie-breaker + withholding relief.",
]

# ── Stay-and-optimise: LEGAL SA tax-efficiency levers (legislated reliefs) ──────
# Factual information only - NOT advice and NOT a designed scheme. Each lever is a
# real statutory relief with its own conditions; SARS GAAR strikes down artificial,
# no-substance arrangements. A registered tax practitioner must confirm + implement.
_LEVERS = [
    {"lever": "Retirement-fund contributions", "section": "s11F", "applies_to": {"employment", "business", "rental", "interest", "pension"},
     "what": "Contributions to a pension / provident / retirement-annuity fund are DEDUCTIBLE from taxable income - the single biggest legal lever for most earners; the fund's growth is tax-free.",
     "indicative": "Deduct up to 27.5% of the greater of remuneration or taxable income, capped at R350,000/yr (R430,000 from 2027)."},
    {"lever": "Tax-free savings account (TFSA)", "section": "s12T", "applies_to": "all",
     "what": "All interest, dividends, capital growth and withdrawals inside a TFSA are completely tax-free.",
     "indicative": "R36,000/yr, R500,000 lifetime."},
    {"lever": "Foreign-employment income exemption", "section": "s10(1)(o)(ii)", "applies_to": {"employment"},
     "what": "If you work abroad >183 days (including 60 continuous) in a 12-month period while still SA-resident, the first R1.25m of that foreign employment income is EXEMPT - a 'work-abroad' route that does NOT require full emigration.",
     "indicative": "First R1,250,000/yr of qualifying foreign employment income exempt."},
    {"lever": "Annual interest exemption", "section": "s10(1)(i)", "applies_to": {"interest"},
     "what": "A slice of local interest income is tax-free every year.",
     "indicative": "R23,800/yr (under 65) or R34,500/yr (65+)."},
    {"lever": "Capital-gains exclusions + timing", "section": "8th Schedule", "applies_to": {"capital_gains"},
     "what": "Only 40% of a net capital gain is taxed (max ~18% effective); the first R40,000/yr is excluded and the first R2,000,000 of gain on your PRIMARY RESIDENCE is excluded. Spreading disposals across tax years uses multiple annual exclusions.",
     "indicative": "R40,000/yr annual exclusion (R50k from 2027) + R2,000,000 primary-residence exclusion (R3m from 2027); 40% inclusion."},
    {"lever": "Local dividends are already lightly taxed", "section": "Dividends Withholding Tax", "applies_to": {"dividends"},
     "what": "Local dividends bear a final 20% withholding tax and NO further income tax - already efficient. (Artificially converting salary into dividends to dodge PAYE invites GAAR - keep it genuine.)",
     "indicative": "20% final; no additional personal income tax."},
    {"lever": "Small Business Corporation rates", "section": "s12E", "applies_to": {"business"},
     "what": "A qualifying SBC pays REDUCED graduated rates instead of the flat 27% company rate, plus accelerated asset write-offs.",
     "indicative": "0% up to R95,750, then 7% / 21% / 27%; 100% (manufacturing) or 50:30:20 asset write-offs."},
    {"lever": "Business incentives (learnerships, R&D, renewables)", "section": "s12H / s11D / s12BA", "applies_to": {"business"},
     "what": "Registered learnership allowances (s12H), approved R&D (150%, s11D) and renewable-energy assets (s12BA) give extra deductions for genuine qualifying activity. (Imara's tax_optimizer models these in the business report.)",
     "indicative": "Per-learner allowances; 150% R&D deduction; enhanced renewable-energy write-off."},
    {"lever": "Section 18A donations", "section": "s18A", "applies_to": "all",
     "what": "Donations to approved public-benefit organisations are deductible (you also do good); excess carries forward.",
     "indicative": "Up to 10% of taxable income, with a valid s18A receipt."},
    {"lever": "Medical tax credits", "section": "s6A / s6B", "applies_to": "all",
     "what": "Fixed monthly credits for medical-scheme membership, plus an additional credit for high out-of-pocket costs, reduce tax directly.",
     "indicative": "~R364/month main member + first dependant, ~R246 each further (2025/26)."},
    {"lever": "Employment Tax Incentive (ETI)", "section": "ETI Act 26/2013", "applies_to": {"business"},
     "what": "An employer hiring qualifying young workers (18-29) or staff in a special economic zone reduces the PAYE it pays to SARS - a direct cash subsidy for GENUINE employment, claimed via EMP201.",
     "indicative": "Up to R2,500/month per qualifying employee earning < R7,500/month (from 1 Apr 2025); full for the first 12 months, half for months 13-24."},
    {"lever": "Capital allowances / wear-and-tear", "section": "s11(e) / s12C / s13quin / s13sex", "applies_to": {"business", "rental"},
     "what": "Genuine business assets are written off against income: wear-and-tear on equipment (s11(e)), accelerated 40/20/20/20 on manufacturing plant (s12C), and 5%/yr on commercial buildings (s13quin) or qualifying residential units (s13sex).",
     "indicative": "Asset-class rates per the SARS wear-and-tear schedule; 5%/yr on qualifying buildings."},
    {"lever": "Assessed-loss carry-forward", "section": "s20", "applies_to": {"business", "rental"},
     "what": "A genuine trading or rental loss is carried forward and set off against future taxable income from that trade, smoothing tax across good and bad years.",
     "indicative": "Companies: offset capped at the greater of R1m or 80% of taxable income per year (excess carries forward); individuals carry the balance forward."},
    {"lever": "Foreign tax credit (relief from double tax)", "section": "s6quat", "applies_to": {"dividends", "interest", "capital_gains", "business"},
     "what": "Foreign tax already paid on the same income is credited against your SA tax so it is not taxed twice; from 1 Mar 2025 this fully covers foreign capital-gains tax and any unused credit carries forward.",
     "indicative": "Credit = foreign tax paid, limited to the SA tax on that foreign income; up to a 6-year carry-forward of the excess."},
    {"lever": "Tax-free retirement lump sum", "section": "Retirement lump-sum table", "applies_to": {"pension"},
     "what": "On retirement (or severance/death) the first slice of a retirement-fund lump sum is taxed at 0%, with a favourable rising table above that - distinct from, and on top of, the s11F contribution deduction.",
     "indicative": "First R550,000 of the cumulative retirement/severance lump sum is tax-free (2025/26)."},
    {"lever": "Travel allowance / reimbursive travel", "section": "s8(1)", "applies_to": {"employment"},
     "what": "The business-travel portion of a structured travel allowance (or per-km reimbursement) is not taxed, where a logbook supports the genuine business kilometres.",
     "indicative": "Up to 80% of a fixed allowance excluded from PAYE where >=80% of use is business; or the SARS-prescribed reimbursive rate per km."},
    {"lever": "Home-office deduction", "section": "s11(a) / s23(b)", "applies_to": {"employment", "business"},
     "what": "Where part of the home is used regularly and exclusively for trade (and, for employees, more than half the work is done there), a proportionate share of rent/bond interest, rates, electricity and repairs is deductible.",
     "indicative": "Deduct the floor-area % of qualifying home running costs (keep records; it reduces the CGT primary-residence exclusion on that portion)."},
    {"lever": "Bona fide bursaries to staff & relatives", "section": "s10(1)(q) / (qA)", "applies_to": {"business"},
     "what": "A genuine bursary or scholarship an employer grants to an employee, or to an employee's relative, is exempt up to set limits - a tax-efficient way to fund education and reward staff.",
     "indicative": "Relative bursaries exempt up to R20,000 (NQF 1-4) / R60,000 (NQF 5-10), where the employee earns <= R600,000/yr."},
]


def stay_and_optimise(income):
    """Legal SA tax-efficiency levers relevant to the income mix (factual, not advice)."""
    income = income if isinstance(income, set) else set()
    out = []
    for lv in _LEVERS:
        a = lv["applies_to"]
        if a == "all" or not income or (isinstance(a, set) and bool(income & a)):
            out.append({k: lv[k] for k in ("lever", "section", "what", "indicative")})
    return out


def _norm_income(income_types):
    """Coerce arbitrary input into a clean set of known income types."""
    if isinstance(income_types, str):
        income_types = [income_types]
    if not isinstance(income_types, (list, tuple, set)):
        return set()
    out = set()
    for t in income_types:
        try:
            t = str(t).strip().lower().replace(" ", "_").replace("-", "_")
        except Exception:
            continue
        if t in INCOME_TYPES:
            out.add(t)
    return out


def _fit(income, code):
    """Deterministic fit hint (strong / possible / weak) for an income mix + destination."""
    passive = bool(income & {"dividends", "interest", "rental", "capital_gains"})
    active = bool(income & {"employment", "business"})
    pension = "pension" in income
    if code == "AE":
        if active or not income:
            return {"level": "strong", "reason": "0% personal tax suits employment/active income; watch 9% corporate tax on UAE business profit and the substance requirement."}
        return {"level": "possible", "reason": "0% personal tax also covers passive income; main effort is meeting the substance/residency test."}
    if code == "CY":
        if passive:
            return {"level": "strong", "reason": "Non-dom gives 0% SDC on dividends/interest/rental — strongest for passive-income-heavy profiles."}
        return {"level": "possible", "reason": "Salaries still hit the PIT scale; the non-dom benefit mainly helps passive income."}
    if code == "PT":
        if pension and not (active or passive):
            return {"level": "weak", "reason": "IFICI EXCLUDES pensions — a pension-only profile gets little benefit (unlike the old NHR)."}
        return {"level": "possible", "reason": "Only strong IF you qualify for the narrow IFICI eligibility (qualifying innovation/high-value role + degree + no PT residence in 5 years); otherwise normal rates apply."}
    if code == "MU":
        if passive:
            return {"level": "strong", "reason": "Remittance basis keeps un-remitted foreign dividends/interest/rental at 0%, and Mauritius has NO capital gains tax - strong for passive and capital-gains-heavy profiles."}
        return {"level": "possible", "reason": "Local income hits the 0%-20% scale; the remittance basis and zero CGT help most when income is foreign and kept offshore."}
    if code == "MT":
        if passive:
            return {"level": "strong", "reason": "Non-dom remittance basis keeps un-remitted foreign passive income at 0%, and foreign capital gains are untaxed even if remitted - strong for passive-heavy profiles."}
        return {"level": "possible", "reason": "Malta-source salary hits the scale (up to 35%); the non-dom benefit mainly helps foreign passive income and gains."}
    if code in ("GR", "IT", "CH"):
        return {"level": "possible", "reason": "A FIXED-FEE regime - it only beats SA tax for very high earners. Provide income amounts to model whether the fixed fee is below your current SA tax."}
    return {"level": "unknown", "reason": "Not in the modelled corpus."}


def relocation_first_pass(profile):
    """Decision-support relocation/tax first-pass. profile = {origin, income_types[], destinations[]}.

    Returns a structured, dated, sourced dict. NOT advice. Robust to malformed input.
    """
    profile = profile if isinstance(profile, dict) else {}
    income = _norm_income(profile.get("income_types"))
    origin = str(profile.get("origin") or "ZA").upper()

    # Optional income amounts -> indicative quantification (SA-origin only; corpus holds SA rates).
    raw_amounts = profile.get("income")
    income_amounts = {}
    if isinstance(raw_amounts, dict):
        for k, v in raw_amounts.items():
            key = str(k).strip().lower()
            if key in INCOME_TYPES:
                income_amounts[key] = _num(v)
    if income_amounts and not income:
        income = {k for k, v in income_amounts.items() if v > 0}
    quantify = bool(income_amounts) and origin == "ZA" and sum(income_amounts.values()) > 0
    age = int(_num(profile.get("age")))
    deductions = profile.get("deductions") if isinstance(profile.get("deductions"), dict) else {}
    current_sa_tax = round(_sa_current_tax(income_amounts, age, deductions), 2) if quantify else None
    goal = str(profile.get("goal") or "").strip().lower()
    if goal not in ("stay", "relocate", "work_abroad"):
        goal = ""
    days_abroad = int(_num(profile.get("days_abroad")))
    residency_note = None
    if days_abroad:
        if days_abroad > 183:
            residency_note = ("You indicated ~{} days/yr outside SA. Working abroad >183 days (including a 60-day "
                              "continuous block) in a 12-month period can make the first R1.25m of FOREIGN EMPLOYMENT "
                              "income exempt (s10(1)(o)(ii)) WITHOUT emigrating; >330 continuous days also bears on "
                              "ceasing residency. Confirm with an advisor.").format(days_abroad)
        else:
            residency_note = ("You indicated ~{} days/yr outside SA - below the 183-day (and 60-day continuous) "
                              "threshold, so the s10(1)(o)(ii) foreign-employment exemption would NOT yet apply.").format(days_abroad)

    want = profile.get("destinations")
    if isinstance(want, str):
        want = [want]
    codes = [str(c).upper() for c in want] if want else list(DESTINATIONS.keys())
    codes = [c for c in codes if c in DESTINATIONS] or list(DESTINATIONS.keys())

    dests = []
    for c in codes:
        d = DESTINATIONS[c]
        treatment = d["income_treatment"]
        # show only the income types the user actually has (or all, if none specified)
        shown = {k: treatment[k] for k in (income or set(INCOME_TYPES)) if k in treatment}
        en = _ENRICH.get(c, {})
        regime = en.get("regime", "rate")
        card = {
            "code": c, "name": d["name"], "regime": regime,
            "residency_test": d["residency_test"], "investment_route": en.get("investment_route", ""),
            "substance": en.get("substance", ""), "dta_with_sa": en.get("dta_with_sa", True),
            "headline": d["headline"], "income_treatment": shown, "gotchas": d["gotchas"],
            "fit": _fit(income, c), "sources": d["sources"],
        }
        if regime == "flat_fee":
            card["flat_fee"] = {"amount_zar": d.get("flat_fee_zar"), "local": d.get("flat_fee_local"), "note": d.get("flat_fee_note")}
        if quantify:
            if regime == "flat_fee":
                dt = round(float(d.get("flat_fee_zar") or 0), 2)
            else:
                dt = round(_dest_tax(income_amounts, d.get("effective_rates", {})), 2)
            card["indicative_destination_tax"] = dt
            card["indicative_annual_saving"] = round(current_sa_tax - dt, 2)
            card["saving_pct"] = round((current_sa_tax - dt) / current_sa_tax * 100, 1) if current_sa_tax > 0 else 0.0
            if regime == "flat_fee" and current_sa_tax > 0:
                if dt < current_sa_tax * 0.9:
                    card["fit"] = {"level": "strong", "reason": "Your current SA tax exceeds the fixed fee - the flat-fee regime saves money at your income level."}
                elif dt <= current_sa_tax * 1.1:
                    card["fit"] = {"level": "possible", "reason": "The fixed fee is roughly your current SA tax - marginal; only worth it for non-tax reasons or higher income."}
                else:
                    card["fit"] = {"level": "weak", "reason": "The fixed fee is MORE than your current SA tax - these flat-fee regimes only pay off at much higher incomes."}
        dests.append(card)
    # rank: strong > possible > weak > unknown
    order = {"strong": 0, "possible": 1, "weak": 2, "unknown": 3}
    dests.sort(key=lambda x: order.get(x["fit"]["level"], 9))

    origin_exit = dict(SA_EXIT) if origin == "ZA" else {
        "jurisdiction": origin, "code": origin, "residency_tests": [],
        "exit_charge": "Your origin country's exit/deemed-disposal rules are not in the corpus yet — confirm them with a local advisor before you move.",
        "process": [], "sources": [],
    }
    raw_assets = profile.get("assets")
    if origin == "ZA" and isinstance(raw_assets, dict):
        # s9H deems disposal of WORLDWIDE assets EXCLUDING SA immovable property, retirement-fund
        # interests and personal-use assets. Charge only the "other worldwide" bucket.
        other = _num(raw_assets.get("other_worldwide_market_value")) or _num(raw_assets.get("worldwide_market_value"))
        bc = _num(raw_assets.get("base_cost"))
        excluded = {k: _num(raw_assets.get(k)) for k in ("sa_immovable_property", "retirement_funds", "primary_residence")}
        excluded = {k: v for k, v in excluded.items() if v > 0}
        if other > 0:
            gain = max(0.0, other - bc)
            origin_exit = dict(origin_exit)
            origin_exit["exit_cgt_estimate"] = {
                "deemed_gain": round(gain, 2),
                "indicative_exit_cgt": round(gain * SA_CGT_EFFECTIVE, 2),
                "rate_used": "18% individual max effective CGT (40% inclusion x 45% marginal)",
                "excluded_assets": excluded,
                "basis": ("s9H deems a disposal of worldwide assets the day before you cease SA tax residency, EXCLUDING "
                          "SA immovable property, retirement-fund interests and personal-use assets - only the 'other "
                          "worldwide assets' bucket is charged here. Indicative."),
            }

    return {
        "available": True,
        "as_of": AS_OF,
        "income_types_considered": sorted(income) or list(INCOME_TYPES),
        "quantified": quantify,
        "indicative_current_sa_tax": current_sa_tax,
        "age_considered": age or None,
        "deductions_considered": deductions or None,
        "goal": goal or None,
        "days_abroad_considered": days_abroad or None,
        "residency_note": residency_note,
        "origin_exit": origin_exit,
        "destinations": dests,
        "guardrails": GUARDRAILS,
        "sequencing": SEQUENCING,
        "cost_considerations": COST_CONSIDERATIONS,
        "stay_and_optimise": stay_and_optimise(income),
        "stay_and_optimise_note": ("LEGAL tax-efficiency levers that lawfully reduce your SA tax WITHOUT relocating - the 'stay-and-optimise' "
                       "alternative to the corridors above (" + SA_EFFICIENCY_AS_OF + "). These are legislated reliefs shown as FACTUAL information - "
                       "NOT advice and NOT a designed scheme. You must genuinely meet each lever's conditions; SARS GAAR strikes down artificial, "
                       "no-substance arrangements. A registered tax practitioner must confirm and implement."),
        "fx_assumption": ("Flat-fee regimes (Greece/Italy/Switzerland) converted at ~R" + str(ZAR_PER_EUR) + "/EUR and ~R" + str(ZAR_PER_CHF) + "/CHF (" + FX_AS_OF + ") - indicative."),
        "classification": "decision-support / factual landscape",
        "is_not": "tax, legal, or financial advice, and not a recommendation to adopt any particular arrangement or move to any particular country",
        "estimates_disclaimer": ("All Rand figures are INDICATIVE estimates from headline/effective rates (" + TAX_AS_OF + ") — NOT a "
                       "computation of your actual liability. They ignore most deductions, exemptions, double-tax treaties, timing, regime "
                       "eligibility, and your full facts. Use them only to gauge rough magnitude; a licensed advisor must compute the real numbers."),
        "disclaimer": ("Indicative factual landscape from a dated rule corpus (as of " + AS_OF + "); tax law changes yearly. "
                       "LEGAL relocation + tax efficiency only — never evasion. This first-pass does NOT design or market a "
                       "cross-border arrangement; only a licensed cross-border tax advisor/attorney (with PI insurance) may advise. "
                       "Confirm everything with a licensed professional before acting."),
    }
