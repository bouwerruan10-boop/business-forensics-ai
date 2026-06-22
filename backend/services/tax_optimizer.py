"""
tax_optimizer.py - deterministic SA SME tax-OPTIMISATION engine (legal planning only).

The flip side of the SA tax COMPLIANCE agent: it surfaces legitimate reliefs an SME
likely QUALIFIES for but may be missing - the Small Business Corporation (Section
12E) graduated rates, the Employment Tax Incentive, the turnover-tax option, and the
accelerated-allowance / learnership / SDL reliefs - and quantifies the ZAR saving
where it can be computed deterministically.

DNA: every number is computed HERE by arithmetic (the LLM only narrates); rates live
in the dated `sa_rates` corpus. Everything is framed as compliance-positive,
GAAR-respecting legal planning that MUST be confirmed with a registered tax
practitioner - this is NOT avoidance/evasion and NOT tax advice. Only QUANTIFIED
opportunities feed the headline saving total; eligibility-only flags are listed
separately so the figure is never overstated.
"""
import math
from services import sa_rates

_DISCLAIMER = ("Legal tax planning only - compliance-positive and GAAR-respecting, NOT avoidance/evasion. "
               "These are reliefs you may QUALIFY for; eligibility and current rates must be confirmed with a "
               "registered SA tax practitioner. This is not tax advice.")


def _fnum(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    try:
        raw = str(v).strip()
        neg = raw.startswith("(") and raw.endswith(")")   # accounting negative, e.g. (50,000)
        x = float(raw.replace(" ", "").replace(",", "").replace("R", "").replace("ZAR", "").strip("()"))
        if neg:
            x = -abs(x)
        return x if math.isfinite(x) else None
    except (ValueError, TypeError):
        return None


def _figs(memory):
    raw = getattr(memory, "financial_figures", {}) or {}
    out = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            n = _fnum(v)
            if n is not None:
                out[k] = n
    return out


def _entity_kind(entity_type):
    """True = company/CC (SBC-capable), False = not (sole prop/partnership/trust), None = unknown."""
    t = (entity_type or "").lower()
    if any(k in t for k in ("sole", "proprietor", "partnership", "trust")):
        return False
    if any(k in t for k in ("pty", "company", "(pty)", "close corp", " cc", "cc ", "incorporated", " inc")):
        return True
    return None


def _r(x):
    return "R{:,.0f}".format(x)


def analyze_tax_optimization(memory) -> dict:
    """Deterministic legal tax-optimisation scan. Returns opportunities + a saving
    range (quantified items only). Pure; no LLM; safe when figures are missing.
    Gated to SA taxpayers - these are South African statutory reliefs only."""
    currency = getattr(memory, "currency", "ZAR") or "ZAR"
    country = (getattr(memory, "country", "") or "").lower()
    is_sa = ("south afric" in country) or (currency.upper() == "ZAR") or country in ("za", "rsa", "sa")
    if not is_sa:
        return {"available": False, "as_of": sa_rates.AS_OF, "sbc_tax_year": sa_rates.SBC_TAX_YEAR,
                "currency": currency, "opportunities": [], "quantified_count": 0,
                "total_saving_low": 0, "total_saving_high": 0,
                "summary": "SA tax-optimisation reliefs apply to South African taxpayers only.",
                "disclaimer": _DISCLAIMER}
    figs = _figs(memory)
    turnover = _fnum(getattr(memory, "annual_revenue", 0)) or figs.get("revenue") or 0.0
    taxable = figs.get("net_profit")
    taxable_basis = "net profit"
    if taxable is None:
        taxable = figs.get("operating_profit")
        taxable_basis = "operating profit (net profit not available)"
    headcount = int(_fnum(getattr(memory, "headcount", 0)) or 0)
    entity_type = getattr(memory, "entity_type", "") or ""
    kind = _entity_kind(entity_type)

    opps = []
    q_low = q_high = 0.0

    # 1) SBC / Section 12E — the quantifiable headline relief
    if turnover and turnover <= sa_rates.SBC_GROSS_INCOME_CEILING and kind is not False:
        eligible = "likely" if kind is True else "possibly"
        if taxable and taxable > 0:
            saving = sa_rates.company_flat_tax(taxable) - sa_rates.sbc_tax(taxable)
            saving = round(max(0.0, saving))
            if saving > 0:
                q_low += saving
                q_high += saving
                opps.append({
                    "name": "Small Business Corporation rates (Section 12E)",
                    "eligible": eligible, "quantified": True,
                    "est_saving_low": saving, "est_saving_high": saving,
                    "basis": "Turnover {} <= R20m and taxable income ~{} ({}): SBC graduated rates (0% to R95,750, then 7%/21%/27%) vs the flat 27% company rate.".format(
                        _r(turnover), _r(taxable), taxable_basis),
                    "action": "Confirm SBC qualification and apply the Section 12E rates in your IT14.",
                    "caveat": "Requires ALL shareholders be natural persons holding no other company shares, <=20% income from investment/personal-service, and not a personal-service provider. Verify with your practitioner.",
                })
        else:
            opps.append({
                "name": "Small Business Corporation rates (Section 12E)",
                "eligible": eligible, "quantified": False,
                "est_saving_low": 0, "est_saving_high": 0,
                "basis": "Turnover {} <= R20m: likely SBC-eligible, but taxable income wasn't available to quantify the saving (SBC rates run 0%/7%/21%/27% vs flat 27%).".format(_r(turnover)),
                "action": "Provide taxable income and confirm SBC qualification (Section 12E).",
                "caveat": "Shareholder/income-mix conditions apply; verify with your practitioner.",
            })
        # 1b) Section 12E accelerated capital allowances (flag)
        opps.append({
            "name": "Accelerated capital allowances (Section 12E)",
            "eligible": eligible, "quantified": False,
            "est_saving_low": 0, "est_saving_high": 0,
            "basis": "SBCs write off qualifying assets faster: 100% in year 1 for manufacturing plant; 50/30/20 over three years for other assets.",
            "action": "Apply the accelerated write-off to qualifying assets bought/in-use this year.",
            "caveat": "Depends on your actual asset additions; quantify with your practitioner.",
        })

    # 2) Employment Tax Incentive (flag; can't quantify without employee ages/wages)
    if headcount >= 1:
        per_emp = sa_rates.ETI_MAX_MONTHLY_Y1 * 12
        opps.append({
            "name": "Employment Tax Incentive (ETI)",
            "eligible": "possibly", "quantified": False,
            "est_saving_low": 0, "est_saving_high": 0,
            "basis": "You report {} employee(s). Each qualifying young worker (18-29) earning <R7,500/mo can attract up to R2,500/mo (~{}/yr) in year 1, R1,250/mo in year 2 - a PER-EMPLOYEE benefit claimed for however many of your staff actually qualify (not an aggregate).".format(headcount, _r(per_emp)),
            "action": "Check how many staff are 18-29 earning <R7,500/mo and claim ETI via EMP201.",
            "caveat": "Depends on employee ages, wages, hours and minimum-wage compliance; quantify per qualifying employee with your practitioner.",
        })
        # SDL note
        opps.append({
            "name": "Skills Development Levy position",
            "eligible": "possibly", "quantified": False,
            "est_saving_low": 0, "est_saving_high": 0,
            "basis": "SDL is 1% of payroll, but employers with annual payroll below R500,000 are EXEMPT. With {} staff, confirm whether you're over or under the threshold.".format(headcount),
            "action": "If annual payroll < R500k, ensure you're not paying SDL; if over, ensure SDL is correctly remitted.",
            "caveat": "Needs your actual annual payroll figure.",
        })

    # 3) Turnover-tax option (flag; situational)
    if turnover and turnover <= sa_rates.TURNOVER_TAX_LIMIT:
        opps.append({
            "name": "Turnover-tax option (micro business)",
            "eligible": "possibly", "quantified": False,
            "est_saving_low": 0, "est_saving_high": 0,
            "basis": "Turnover {} <= R2.3m: you may elect the simplified turnover-tax regime (tax on turnover, not profit). It can be simpler and cheaper for low-margin micros - or MORE expensive for high-margin ones.".format(_r(turnover)),
            "action": "Model turnover-tax vs the normal/SBC basis before electing - it's not automatically better.",
            "caveat": "Election has lock-in rules; compare both with your practitioner.",
        })

    # 4) Learnership allowance (Section 12H) - employer skills-development relief
    if headcount >= 1:
        opps.append({
            "name": "Learnership allowance (Section 12H)",
            "eligible": "possibly", "quantified": False,
            "est_saving_low": 0, "est_saving_high": 0,
            "basis": "Each SETA-registered learnership/apprenticeship agreement earns an ANNUAL allowance (R40,000, or R60,000 for a learner with a disability) plus a COMPLETION allowance of the same amount. Available for agreements entered on or before 31 March 2027.",
            "action": "Register qualifying learnerships with your SETA and claim the s12H annual + completion allowances in your IT14.",
            "caveat": "Needs a SETA-registered agreement; per-agreement amounts and the 31 Mar 2027 sunset must be confirmed with your practitioner.",
        })

    # 5) R&D deduction (Section 11D) - 150% on approved R&D
    opps.append({
        "name": "Research & Development deduction (Section 11D)",
        "eligible": "review", "quantified": False,
        "est_saving_low": 0, "est_saving_high": 0,
        "basis": "Approved scientific or technological R&D earns a 150% deduction (R1.5m deductible per R1m spent), extended to 31 December 2033. Often missed by SMEs developing new products, software or processes.",
        "action": "If you develop new products/processes/software, apply to the DSI for s11D pre-approval (the 50% uplift applies only from the approval-application date).",
        "caveat": "Requires DSI approval; routine/non-qualifying work is excluded - confirm scope with your practitioner.",
    })

    # 6) Energy & renewables (Section 12B permanent; Section 12L efficiency)
    opps.append({
        "name": "Energy & renewable-asset allowances (Section 12B / 12L)",
        "eligible": "review", "quantified": False,
        "est_saving_low": 0, "est_saving_high": 0,
        "basis": "Section 12B gives an accelerated write-off on renewable-generation assets (e.g. solar PV) and is PERMANENT; Section 12L gives 95c per kWh of verified energy-efficiency savings (extended to 31 December 2030). NOTE: the enhanced 125% Section 12BA allowance EXPIRED for assets brought into use after 28 February 2025 - do not assume it.",
        "action": "If you've invested (or plan to) in solar/renewables or efficiency measures, claim s12B and/or have s12L savings verified by a SANEDI-accredited M&V body.",
        "caveat": "s12B rates depend on asset type/size; s12L needs accredited measurement. Confirm current rules with your practitioner.",
    })

    # 7) Doubtful-debt allowance (Section 11(j)) - timing benefit on aged debtors
    opps.append({
        "name": "Doubtful-debt allowance (Section 11(j))",
        "eligible": "review", "quantified": False,
        "est_saving_low": 0, "est_saving_high": 0,
        "basis": "If you carry aged trade debtors, s11(j) allows a deduction (generally 25%, rising to 40% on debts 120+ days overdue) for doubtful debts WITHOUT writing them off - a timing benefit many SMEs overlook.",
        "action": "Apply the s11(j) doubtful-debt allowance to your aged-debtor book in the IT14.",
        "caveat": "Based on your actual debtor ageing; quantify with your practitioner.",
    })

    # 8) Donations to PBOs (Section 18A) - only meaningful where there is taxable income
    if taxable and taxable > 0:
        opps.append({
            "name": "Donations to PBOs (Section 18A)",
            "eligible": "review", "quantified": False,
            "est_saving_low": 0, "est_saving_high": 0,
            "basis": "Bona fide donations to s18A-approved public benefit organisations are deductible up to 10% of taxable income, with any excess carried forward - a genuine CSI/giving programme can be tax-efficient.",
            "action": "Obtain valid s18A certificates for donations and claim the deduction (cap 10% of taxable income).",
            "caveat": "Only s18A-approved PBOs qualify and a valid s18A certificate is required.",
        })

    # 9) Residual pointer to further fact-specific reliefs
    opps.append({
        "name": "Further reliefs to review",
        "eligible": "review", "quantified": False,
        "est_saving_low": 0, "est_saving_high": 0,
        "basis": "Also commonly missed: wear-and-tear (Section 11(e)) and the 50/30/20 plant write-off (Section 12C), prepaid-expense timing (Section 23H), and bad-debt write-offs (Section 11(i)).",
        "action": "Ask your practitioner which of these apply to your operations.",
        "caveat": "Eligibility is fact-specific.",
    })

    quantified = [o for o in opps if o["quantified"]]
    summary = (
        "{} potential relief(s) identified; estimated quantifiable saving ~{}{} (mainly SBC), "
        "plus {} further opportunit(y/ies) to quantify with a registered tax practitioner.".format(
            len(opps), currency + " ", _r(q_high) if q_high else "0",
            len(opps) - len(quantified))
    ) if opps else "No specific SA tax-optimisation reliefs were identified from the data provided."

    return {
        "available": bool(opps),
        "as_of": sa_rates.AS_OF,
        "sbc_tax_year": sa_rates.SBC_TAX_YEAR,
        "currency": currency,
        "opportunities": opps,
        "quantified_count": len(quantified),
        "total_saving_low": round(q_low),
        "total_saving_high": round(q_high),
        "summary": summary,
        "disclaimer": _DISCLAIMER,
    }


def tax_optimization_block(memory) -> str:
    """Compact block for the agent's LLM prompt - the computed opportunities the LLM
    must NARRATE using exactly these figures (it must not invent savings)."""
    res = analyze_tax_optimization(memory)
    if not res["available"]:
        return ""
    lines = ["PRE-COMPUTED SA TAX-OPTIMISATION OPPORTUNITIES (legal planning; figures are exact - "
             "narrate these, do NOT invent or recompute savings; frame every item as compliance-positive, "
             "GAAR-respecting, and 'confirm with a registered tax practitioner'):"]
    for o in res["opportunities"]:
        amt = ""
        if o["quantified"]:
            amt = " | est. saving {}".format(_r(o["est_saving_high"]))
        elif o["est_saving_high"]:
            amt = " | up to {} (theoretical ceiling, NOT confirmed)".format(_r(o["est_saving_high"]))
        lines.append("- [{}] {}{} - {} Action: {} ({})".format(
            o["eligible"], o["name"], amt, o["basis"], o["action"], o["caveat"]))
    lines.append("HEADLINE quantifiable saving (SBC etc.): ~{} (as of {}, SBC table {}).".format(
        _r(res["total_saving_high"]), res["as_of"], res["sbc_tax_year"]))
    return "\n".join(lines)
