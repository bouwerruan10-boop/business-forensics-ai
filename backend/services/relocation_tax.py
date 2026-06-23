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

INCOME_TYPES = ("employment", "business", "dividends", "interest", "rental", "capital_gains", "pension")

# ── Indicative tax quantification (SA 2025/26; sourced) ────────────────────────
# INDICATIVE ONLY — headline/effective rates, NOT a computation of actual liability.
TAX_AS_OF = "SA 2025/26 tax year"
SA_BRACKETS = [(237100, 0.18), (370500, 0.26), (512800, 0.31), (673000, 0.36),
               (857900, 0.39), (1817000, 0.41), (float("inf"), 0.45)]
SA_PRIMARY_REBATE = 17235     # 2025/26 primary rebate
SA_DIV_WHT = 0.20             # dividends withholding (final)
SA_CGT_EFFECTIVE = 0.18       # individual max effective CGT (40% inclusion x 45%)


def _num(v):
    """Coerce arbitrary input to a non-negative float; junk -> 0.0."""
    try:
        f = float(v)
        return f if f > 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


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


def _sa_current_tax(income):
    """Indicative current SA personal tax on an income dict (type -> amount)."""
    ordinary = sum(_num(income.get(k)) for k in ("employment", "business", "interest", "rental", "pension"))
    return _sa_income_tax(ordinary) + _num(income.get("dividends")) * SA_DIV_WHT + _num(income.get("capital_gains")) * SA_CGT_EFFECTIVE


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
}

GUARDRAILS = [
    {"title": "Exit tax first", "detail": "Leaving your current country can trigger an exit/deemed-disposal CGT (e.g. SA s9H) before you arrive anywhere. Model the cost of LEAVING, not just the destination rate."},
    {"title": "Substance over form (GAAR)", "detail": "You must GENUINELY relocate — real home, real days, real ties. A sham move, a mailbox, or round-tripping fails anti-avoidance rules (GAAR) and can carry promoter/penalty exposure."},
    {"title": "Transparency is the default (CRS)", "detail": "Under the CRS your financial accounts are reported automatically between countries (CARF extends this to crypto). This is about LEGAL relocation, not hiding income — assume everything is visible to tax authorities."},
    {"title": "This is information, not an arrangement (DAC6/MDR)", "detail": "Designing or marketing a reportable cross-border tax arrangement makes the designer an 'intermediary' with disclosure duties and penalties. This tool gives you the factual landscape; it does not design or recommend a specific arrangement."},
    {"title": "Use a licensed advisor", "detail": "Only a licensed cross-border tax advisor / attorney (with professional-indemnity insurance) may ADVISE on or implement any of this. Treat this first-pass as preparation for that conversation, not a substitute for it."},
]


def _norm_income(income_types):
    """Coerce arbitrary input into a clean set of known income types."""
    if isinstance(income_types, str):
        income_types = [income_types]
    out = set()
    for t in (income_types or []):
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
    current_sa_tax = round(_sa_current_tax(income_amounts), 2) if quantify else None

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
        card = {
            "code": c, "name": d["name"], "residency_test": d["residency_test"],
            "headline": d["headline"], "income_treatment": shown, "gotchas": d["gotchas"],
            "fit": _fit(income, c), "sources": d["sources"],
        }
        if quantify:
            dt = round(_dest_tax(income_amounts, d.get("effective_rates", {})), 2)
            card["indicative_destination_tax"] = dt
            card["indicative_annual_saving"] = round(current_sa_tax - dt, 2)
            card["saving_pct"] = round((current_sa_tax - dt) / current_sa_tax * 100, 1) if current_sa_tax > 0 else 0.0
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
        mv = _num(raw_assets.get("worldwide_market_value"))
        bc = _num(raw_assets.get("base_cost"))
        if mv > 0:
            gain = max(0.0, mv - bc)
            origin_exit = dict(origin_exit)
            origin_exit["exit_cgt_estimate"] = {
                "deemed_gain": round(gain, 2),
                "indicative_exit_cgt": round(gain * SA_CGT_EFFECTIVE, 2),
                "rate_used": "18% individual max effective CGT (40% inclusion x 45% marginal)",
                "basis": ("s9H deems a disposal of worldwide assets at market value the day before you cease SA tax residency. "
                          "SA immovable property is EXCLUDED (stays in the SA net) — exclude it from market value above. Indicative only."),
            }

    return {
        "available": True,
        "as_of": AS_OF,
        "income_types_considered": sorted(income) or list(INCOME_TYPES),
        "quantified": quantify,
        "indicative_current_sa_tax": current_sa_tax,
        "origin_exit": origin_exit,
        "destinations": dests,
        "guardrails": GUARDRAILS,
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
