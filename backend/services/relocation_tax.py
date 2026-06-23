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
        dests.append({
            "code": c, "name": d["name"], "residency_test": d["residency_test"],
            "headline": d["headline"], "income_treatment": shown, "gotchas": d["gotchas"],
            "fit": _fit(income, c), "sources": d["sources"],
        })
    # rank: strong > possible > weak > unknown
    order = {"strong": 0, "possible": 1, "weak": 2, "unknown": 3}
    dests.sort(key=lambda x: order.get(x["fit"]["level"], 9))

    origin_exit = SA_EXIT if origin == "ZA" else {
        "jurisdiction": origin, "code": origin, "residency_tests": [],
        "exit_charge": "Your origin country's exit/deemed-disposal rules are not in the corpus yet — confirm them with a local advisor before you move.",
        "process": [], "sources": [],
    }

    return {
        "available": True,
        "as_of": AS_OF,
        "income_types_considered": sorted(income) or list(INCOME_TYPES),
        "origin_exit": origin_exit,
        "destinations": dests,
        "guardrails": GUARDRAILS,
        "classification": "decision-support / factual landscape",
        "is_not": "tax, legal, or financial advice, and not a recommendation to adopt any particular arrangement or move to any particular country",
        "disclaimer": ("Indicative factual landscape from a dated rule corpus (as of " + AS_OF + "); tax law changes yearly. "
                       "LEGAL relocation + tax efficiency only — never evasion. This first-pass does NOT design or market a "
                       "cross-border arrangement; only a licensed cross-border tax advisor/attorney (with PI insurance) may advise. "
                       "Confirm everything with a licensed professional before acting."),
    }
