"""
tax_risk_flags.py - deterministic SA "GAAR / SARS-scrutiny" structural-risk scanner.

The mirror image of tax_optimizer.py. Where the optimiser surfaces legitimate reliefs
an SME may be MISSING, this surfaces STRUCTURAL patterns in the business that commonly
attract scrutiny under the General Anti-Avoidance Rule (Income Tax Act ss 80A-80L),
transfer pricing (s31), or routine SARS audit selection - so the owner can make sure
each arrangement has genuine commercial substance and documentation BEFORE a lender or
SARS asks.

DNA / guardrails:
- Deterministic and pure: pattern + arithmetic detection only; the LLM merely narrates.
- These are RISK-AWARENESS flags, NOT findings of wrongdoing or accusations of evasion,
  and NOT advice. Every flag points at substance/documentation and "confirm with a
  registered tax practitioner".
- Conservative: a flag fires only on a clear signal; absence of a flag is reported as a
  clean result, never as assurance.
"""
import math
from services import sa_rates

_DISCLAIMER = ("Risk-awareness only: these are STRUCTURAL patterns that can attract SARS or GAAR "
               "(Income Tax Act ss 80A-80L) scrutiny - NOT findings of wrongdoing. Ensure each "
               "arrangement has genuine commercial substance and contemporaneous documentation, and "
               "confirm your position with a registered SA tax practitioner. This is not tax or legal advice.")

_SEV_RANK = {"low": 1, "medium": 2, "high": 3}


def _fnum(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    try:
        raw = str(v).strip()
        neg = raw.startswith("(") and raw.endswith(")")
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
                out[str(k).lower()] = n
    return out


def _first(figs, *keys):
    for k in keys:
        if k in figs:
            return figs[k]
    return None


def _doc_blob(memory):
    parts = []
    for attr in ("uploaded_financial_text", "uploaded_bank_text", "uploaded_legal_text",
                 "uploaded_hr_text", "uploaded_plan_text"):
        t = getattr(memory, attr, "") or ""
        if t:
            parts.append(str(t))
    return "\n".join(parts).lower()


def _matched(blob, terms):
    return sorted({t for t in terms if t in blob})


def analyze_tax_risk_flags(memory) -> dict:
    """Deterministic GAAR/SARS structural-risk scan. Pure; safe when figures/text are missing."""
    currency = getattr(memory, "currency", "ZAR") or "ZAR"
    country = (getattr(memory, "country", "") or "").lower()
    is_sa = ("south afric" in country) or (currency.upper() == "ZAR") or country in ("za", "rsa", "sa")
    if not is_sa:
        return {"available": False, "as_of": sa_rates.AS_OF, "currency": currency, "flags": [],
                "flag_count": 0, "risk_band": "none",
                "summary": "GAAR/SARS structural-risk scanning applies to South African taxpayers only.",
                "disclaimer": _DISCLAIMER}

    figs = _figs(memory)
    blob = _doc_blob(memory)
    turnover = _fnum(getattr(memory, "annual_revenue", 0)) or figs.get("revenue") or 0.0
    pbt = _first(figs, "profit_before_tax", "pbt", "net_profit", "net_income", "operating_profit")
    tax_exp = _first(figs, "tax", "tax_expense", "income_tax", "taxation", "company_tax")
    vat_registered = str(getattr(memory, "vat_registered", "") or "").strip().lower()

    flags = []

    # 1) Related-party / connected-person / management-fee structures (GAAR ss80A-80L; s31 transfer pricing)
    rp_terms = ["management fee", "management fees", "related party", "related-party",
                "connected person", "connected-person", "intercompany", "inter-company",
                "inter company", "shareholder loan", "loan to director", "director's loan",
                "directors loan", "associated company", "associated entity", "group company"]
    rp = _matched(blob, rp_terms)
    if rp:
        flags.append({
            "code": "related_party",
            "title": "Related-party / connected-person arrangements",
            "severity": "medium",
            "detail": "The documents reference {}. Transactions between connected persons (management fees, intercompany charges, shareholder/director loans) are a primary SARS focus.".format(", ".join(rp[:4])),
            "basis": "GAAR (ss 80A-80L) requires commercial substance, not a tax-benefit main purpose; transfer pricing (s31) requires connected-party cross-border dealings to be arm's-length; director loans can trigger deemed dividends (s64E).",
            "action": "Keep written agreements, arm's-length pricing support and board minutes for every related-party charge; confirm treatment with your practitioner.",
        })

    # 2) Offshore / low-tax-jurisdiction indicators (GAAR; s31 transfer pricing; CFC s9D; exchange control)
    off_terms = ["offshore", "mauritius", "cayman", "bvi", "british virgin", "seychelles",
                 "isle of man", "jersey", "guernsey", "delaware", "dubai", "uae",
                 "luxembourg", "tax haven", "ip holding", "royalty to", "offshore trust"]
    off = _matched(blob, off_terms)
    if off:
        flags.append({
            "code": "offshore_structure",
            "title": "Cross-border / low-tax-jurisdiction structure",
            "severity": "high",
            "detail": "The documents reference {}. Arrangements routing income, IP or royalties through low-tax jurisdictions are the highest-scrutiny GAAR/transfer-pricing category.".format(", ".join(off[:4])),
            "basis": "GAAR (ss 80A-80L), transfer pricing (s31), controlled-foreign-company rules (s9D) and SARB exchange control all apply; substance-over-form and arm's-length pricing are decisive.",
            "action": "Ensure genuine economic substance offshore (people, functions, assets), arm's-length pricing, CFC disclosure and exchange-control approval; review with a cross-border tax specialist.",
        })

    # 3) Effective-tax-rate anomaly (very low tax vs profit, if not explained)
    if pbt is not None and pbt > 0 and tax_exp is not None and tax_exp >= 0:
        etr = (tax_exp / pbt) * 100.0
        if etr < 10.0:
            flags.append({
                "code": "low_effective_tax",
                "title": "Low effective tax rate relative to profit",
                "severity": "medium",
                "detail": "Implied effective tax rate is ~{:.1f}% on profit before tax of R{:,.0f}, well below the 27% company rate.".format(etr, pbt),
                "basis": "A low ETR is legitimate when driven by SBC rates, assessed losses or capital allowances - but an UNEXPLAINED low ETR is a common SARS audit-selection trigger.",
                "action": "Make sure your tax computation reconciles profit to tax with documented permanent/timing differences (SBC, s11/s12 allowances, assessed losses).",
            })

    # 4) Sustained loss alongside real turnover (assessed-loss scrutiny; s20 ring-fencing/utilisation cap)
    if turnover and turnover >= 1_000_000 and pbt is not None and pbt <= 0:
        flags.append({
            "code": "loss_with_turnover",
            "title": "Operating loss alongside substantial turnover",
            "severity": "low",
            "detail": "Reported turnover ~R{:,.0f} with a non-positive profit before tax. Persistent losses against real revenue draw SARS review.".format(turnover),
            "basis": "Assessed losses must be genuine; s20 caps loss utilisation at the higher of R1m or 80% of taxable income, and sustained losses can attract audit and (for non-companies) s20A ring-fencing.",
            "action": "Retain evidence that losses are commercial (not arranged), and track the s20 carry-forward/utilisation correctly.",
        })

    # 5) VAT compulsory-registration gap (SARS compliance scrutiny)
    if turnover and turnover >= sa_rates.VAT_COMPULSORY_THRESHOLD and vat_registered not in ("yes", "true", "registered", "y"):
        flags.append({
            "code": "vat_threshold_gap",
            "title": "Turnover above the compulsory VAT-registration threshold",
            "severity": "medium",
            "detail": "Turnover ~R{:,.0f} is at/above the R{:,.0f} compulsory VAT threshold, but the profile does not show active VAT registration.".format(turnover, sa_rates.VAT_COMPULSORY_THRESHOLD),
            "basis": "VAT Act 89/1991: registration is compulsory once taxable supplies exceed the threshold in any 12 months; trading above it unregistered is a frequent SARS trigger and carries penalties + interest.",
            "action": "Confirm your 12-month taxable-supply total and register for VAT if the threshold is exceeded; regularise any past period with your practitioner.",
        })

    # 6) Cash-intensive + bank-inflows materially above declared turnover (unrecorded-income risk)
    inflows = _first(figs, "bank_inflows", "deposits", "total_deposits", "cash_inflows")
    if inflows is not None and turnover and inflows > turnover * 1.30 and inflows > 0:
        flags.append({
            "code": "inflow_turnover_gap",
            "title": "Bank inflows materially exceed declared turnover",
            "severity": "high",
            "detail": "Bank inflows ~R{:,.0f} exceed declared turnover ~R{:,.0f} by more than 30%. Unexplained gaps suggest possible unrecorded income.".format(inflows, turnover),
            "basis": "SARS routinely reconciles bank deposits to declared income/VAT output; an unexplained excess is a strong audit and understatement-penalty trigger (Tax Administration Act).",
            "action": "Reconcile every non-income deposit (loans, capital, transfers, refunds) with documentation so the gap is fully explained.",
        })

    if not flags:
        return {"available": True, "as_of": sa_rates.AS_OF, "currency": currency, "flags": [],
                "flag_count": 0, "risk_band": "none",
                "summary": "No structural GAAR/SARS-scrutiny indicators were detected from the data provided. (Absence of flags is not assurance - it reflects only what was supplied.)",
                "disclaimer": _DISCLAIMER}

    band = max(flags, key=lambda f: _SEV_RANK.get(f["severity"], 0))["severity"]
    n_high = sum(1 for f in flags if f["severity"] == "high")
    n_med = sum(1 for f in flags if f["severity"] == "medium")
    n_low = sum(1 for f in flags if f["severity"] == "low")
    summary = ("{} structural tax-risk flag(s) detected ({} high, {} medium, {} low). These are patterns "
               "that commonly attract SARS/GAAR scrutiny - ensure commercial substance and documentation; "
               "they are not findings of wrongdoing.").format(len(flags), n_high, n_med, n_low)

    return {
        "available": True,
        "as_of": sa_rates.AS_OF,
        "currency": currency,
        "flags": flags,
        "flag_count": len(flags),
        "risk_band": band,
        "summary": summary,
        "disclaimer": _DISCLAIMER,
    }


def tax_risk_block(memory) -> str:
    """Compact block for the agent's LLM prompt - the deterministically-detected flags the LLM
    must NARRATE defensively (risk-awareness, substance/documentation; never an accusation)."""
    res = analyze_tax_risk_flags(memory)
    if not res.get("available") or not res.get("flags"):
        return ""
    lines = ["PRE-DETECTED STRUCTURAL TAX-RISK FLAGS (GAAR ss80A-80L / SARS scrutiny). Narrate these "
             "defensively as risk-awareness items - NOT accusations of evasion - and always point at "
             "commercial substance, documentation, and 'confirm with a registered tax practitioner':"]
    for f in res["flags"]:
        lines.append("- [{}] {} - {} Basis: {} Action: {}".format(
            f["severity"], f["title"], f["detail"], f["basis"], f["action"]))
    lines.append("Overall structural-risk band: {}.".format(res["risk_band"]))
    return "\n".join(lines)
