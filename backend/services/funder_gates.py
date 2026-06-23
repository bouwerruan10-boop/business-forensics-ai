"""
Funder gates — deterministic, decision-support.

Imara's `funding_fit` maps a firm to funding ARCHETYPES (revenue-based advance,
term loan, development funding, ...). This module goes one layer deeper: it
evaluates the firm against the PUBLISHED eligibility gates of NAMED South African
funders, so "development funding (e.g. SEFA/IDC/NEF)" becomes a concrete
"you meet / don't meet IDC's R1m + industrial-sector gate, here's why".

Dated corpus (AS_OF 2026-06), sourced:
- SEDFA (the merged SEFA+SEDA+CBDA, 1 Oct 2024): R50k–R15m, registered+viable SMME.
- IDC: R1m–R1bn, industrial sector + jobs/import-replacement + equity + B-BBEE L4.
- NEF (NEFCorp): R250k–R75m, >=50.1% black ownership + black mgmt/board.
- Business Partners (private benchmark): R500k–R50m, viable formal SME; excludes
  direct farming, underground mining, informal/micro, NPOs, on-lending.

Objective information about funding PROVIDERS whose published criteria a profile
like this may meet (FAIS s1(3)(a) analysis/objective-information exemption) — NOT
a recommendation that any provider is suitable, NOT a credit decision, and NOT an
Imara Score input. Deterministic, no LLM in the logic.
"""

AS_OF = "2026-06"

__all__ = ["evaluate_funder_gates"]


def _d(x):
    return x if isinstance(x, dict) else {}


def _txt(x):
    try:
        return str(x) if x is not None else ""
    except Exception:
        return ""


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    import math
    return f if math.isfinite(f) and f >= 0 else None


def _has(text, words):
    t = _txt(text).lower()
    return any(w in t for w in words)


_INDUSTRIAL = ("manufactur", "industr", "energy", "mining", "agro", "agri-process",
               "agriprocess", "engineering", "production", "fabricat", "processing", "textile")
_BP_EXCLUDED = ("underground mining", "informal", "micro-enterprise", "on-lend", "non-profit", "npo", "npc")
_FARMING = ("farming", "primary agriculture")


def _trading_ok(years_in_business):
    s = _txt(years_in_business).lower().strip()
    if not s:
        return None  # unknown
    if s.startswith("<1") or s.startswith("0-1") or s in ("0", "<1 year", "less than 1 year", "0-1 years"):
        return False
    # any digit >=1 anywhere -> treat as >=1 year trading
    import re
    nums = [int(n) for n in re.findall(r"\d+", s)]
    return (max(nums) >= 1) if nums else None


def _registered(entity, cipc):
    if _txt(cipc).strip():
        return True
    return _has(entity, ("pty", "(pty)", "ltd", "limited", "close corporation", " cc", "incorporated", "inc"))


def evaluate_funder_gates(report, profile=None):
    """Evaluate the firm against named SA funders' published gates. JSON-safe, hostile-input-proof."""
    try:
        report = _d(report)
        profile = _d(profile)

        revenue = _num(profile.get("annual_revenue")) or _num(report.get("annual_revenue")) \
            or _num(_d(report.get("financial_figures")).get("revenue")) or 0.0
        entity = (_txt(profile.get("entity_type")) or _txt(report.get("entity_type"))).lower()
        sector = (_txt(report.get("industry")) or _txt(report.get("industry_key")) or _txt(profile.get("industry"))).lower()
        bbbee = (_txt(profile.get("bbbee_level")) or _txt(report.get("bbbee_level"))).lower()
        cipc = _txt(profile.get("cipc_number")) or _txt(report.get("cipc_number"))
        years = _txt(profile.get("years_in_business")) or _txt(report.get("years_in_business"))

        registered = _registered(entity, cipc)
        trading = _trading_ok(years)
        industrial = _has(sector, _INDUSTRIAL)
        is_npo = _has(entity, ("npo", "npc", "non-profit", "non profit"))
        black_signal = _has(bbbee, ("black", "100%", "level 1", "level 2", "eme", "qse"))  # weak proxy only

        funders = []

        def add(key, name, ftype, ticket, fit, checks, why, requirements, caveat, source):
            funders.append({
                "key": key, "name": name, "type": ftype, "ticket_range": ticket,
                "fit": fit, "checks": checks, "why": why,
                "requirements": requirements, "caveat": caveat, "source": source,
            })

        # ── SEDFA (ex-SEFA) — widest SMME mandate, smaller tickets ────────────────
        sedfa_fit = "good" if registered else "possible"
        if revenue and revenue > 50_000_000:
            sedfa_fit = "possible"  # SEDFA targets SMMEs, not large firms
        add("sedfa", "SEDFA (ex-SEFA)", "Government DFI", "R50k–R15m", sedfa_fit,
            [{"gate": "SA-registered & compliant business", "status": "pass" if registered else "unknown",
              "note": "Registered/compliant entity" if registered else "Register with CIPC + ensure compliance first."},
             {"gate": "Operates primarily in South Africa", "status": "pass", "note": "Assumed from profile; confirm."},
             {"gate": "Viable, with sound management", "status": "unknown", "note": "SEDFA assesses viability case-by-case."}],
            "The merged government SMME financier (SEFA+SEDA+CBDA since 1 Oct 2024) — the widest SME mandate, including township/rural (TREP), youth, women, disability and military-veteran schemes; smaller tickets than IDC.",
            "SA-registered + compliant, demonstrably viable, supporting docs; specific schemes for township/rural and designated groups.",
            "Development finance — higher demand and slower process than alt-lenders; bridging/term facilities.",
            "SEDFA / SEFA (sefa.org.za) — eligibility criteria 2025")

        # ── IDC — industrial only, R1m floor ──────────────────────────────────────
        idc_scale_ok = revenue >= 1_000_000 if revenue else None
        if not industrial:
            idc_fit = "unlikely"
        elif idc_scale_ok:
            idc_fit = "possible"
        else:
            idc_fit = "unlikely"
        add("idc", "IDC (Industrial Development Corporation)", "Government DFI", "R1m–R1bn", idc_fit,
            [{"gate": "Industrial / supported sector", "status": "pass" if industrial else "fail",
              "note": "Manufacturing/energy/mining/agro-processing etc." if industrial else "IDC funds INDUSTRIAL sectors — general retail/services usually do not qualify."},
             {"gate": "Minimum R1m funding", "status": ("pass" if idc_scale_ok else "fail") if revenue else "unknown",
              "note": "Scale plausibly supports a >=R1m deal." if idc_scale_ok else "IDC's floor is R1m — smaller needs suit SEDFA."},
             {"gate": "Owner equity contribution", "status": "note", "note": "Start-ups ~50% equity at peak; expansions ~35%."},
             {"gate": "B-BBEE Level 4 minimum", "status": "note", "note": "Required, or an undertaking to reach it."}],
            "Large industrial / expansion / capex funding (R1m–R1bn) tied to new industrial capacity, jobs or import replacement.",
            "Industrial sector, viable model + experienced management, equity contribution, B-BBEE L4 (or undertaking), feasibility + 5-year financials.",
            "Industrial mandate only; documentation-heavy and slow; not general working capital for retail/services.",
            "IDC (idc.co.za) — how IDC funding works / FAQ 2025")

        # ── NEF — empowerment, ownership-gated ────────────────────────────────────
        nef_fit = "possible" if not is_npo else "unlikely"
        add("nef", "NEF (National Empowerment Fund)", "Government DFI", "R250k–R75m", nef_fit,
            [{"gate": ">=50.1% black ownership + black mgmt/board", "status": "pass" if black_signal else "unknown",
              "note": "Ownership signal present in B-BBEE profile (CONFIRM the exact %)." if black_signal else "NEF's core gate — confirm the business is >=50.1% black-owned with black management/board involvement."},
             {"gate": "Ticket R250k–R75m", "status": "pass" if (revenue and 0 < revenue) else "unknown", "note": "Across uMnotho/iMbewu/Rural/Strategic/Women funds."},
             {"gate": "Commercial viability + job creation", "status": "unknown", "note": "Rural/economically-depressed areas and black-women participation are favoured."}],
            "The empowerment financier for black-owned businesses (R250k–R75m) across five specialised funds.",
            ">=50.1% black ownership with black operational/board involvement, commercial viability, legal compliance, job-creation potential.",
            "Empowerment mandate — the ownership threshold is the gating test; confirm the exact black-ownership %.",
            "NEF (nefcorp.co.za) — funding criteria 2025")

        # ── Business Partners — private commercial benchmark ──────────────────────
        bp_excluded = is_npo or _has(sector, _BP_EXCLUDED) or _has(sector, _FARMING)
        bp_scale_ok = (500_000 <= revenue <= 50_000_000) if revenue else None
        if bp_excluded:
            bp_fit = "ineligible"
        elif trading is False:
            bp_fit = "possible"  # Business Partners finances ESTABLISHED SMEs; <1yr trading is a real hurdle
        elif registered and (bp_scale_ok is not False):
            bp_fit = "good"
        else:
            bp_fit = "possible"
        add("business_partners", "Business Partners Limited", "Private SME financier", "R500k–R50m", bp_fit,
            [{"gate": "Established, trading business", "status": "fail" if trading is False else ("pass" if trading else "unknown"),
              "note": "Trading >=1 year." if trading else ("Business Partners finances ESTABLISHED SMEs — under ~1 year trading is a hurdle." if trading is False else "Confirm trading history.")},
             {"gate": "Viable, formally-registered SME", "status": "pass" if registered else "unknown",
              "note": "Formal registration in place." if registered else "Must be a formally registered SME."},
             {"gate": "Not an excluded activity", "status": "fail" if bp_excluded else "pass",
              "note": "Excludes direct farming, underground mining, informal/micro, NPOs and on-lending." if bp_excluded else "Activity not on the exclusion list."},
             {"gate": "Ticket R500k–R50m", "status": ("pass" if bp_scale_ok else "note") if revenue else "unknown",
              "note": "Scale fits the R500k–R50m band." if bp_scale_ok else "Confirm the funding amount sits in R500k–R50m."}],
            "Leading PRIVATE SME risk-financier — holistic assessment (track record + potential), no fixed minimum own-contribution.",
            "Business plan, annual financial statements, management accounts, cash-flow forecast, owner CV; viable formal SME.",
            "Excludes direct farming, underground mining, informal/micro, NPOs and on-lending; typical term 3–5 years.",
            "Business Partners Limited (businesspartners.co.za) 2025")

        order = {"good": 0, "possible": 1, "unlikely": 2, "ineligible": 3}
        funders.sort(key=lambda f: order.get(f["fit"], 9))
        primary = [f["name"] for f in funders if f["fit"] in ("good", "possible")]

        data_gaps = [
            "Confirmed black-ownership % (NEF needs >=50.1%; also affects B-BBEE-linked criteria).",
            "The exact funding amount sought (determines which ticket bands apply).",
            "Use of funds (working capital vs capex/expansion) — DFIs gate on purpose.",
            "Signed/AFS financials + business plan (most DFIs and Business Partners require them).",
        ]

        return {
            "available": True,
            "as_of": AS_OF,
            "funders": funders,
            "primary": primary,
            "data_gaps": data_gaps,
            "is_not": "a recommendation that any funder is suitable for you, a credit decision, or financial advice",
            "disclaimer": ("Objective information about funding PROVIDERS whose PUBLISHED eligibility criteria a profile "
                           "like this may meet (dated " + AS_OF + ") — NOT a recommendation that any provider is suitable, "
                           "NOT a credit decision, and NOT an Imara Score input. Each funder makes its own decision; "
                           "criteria change — confirm current terms directly with the funder."),
        }
    except Exception:
        return {"available": False, "reason": "Funder-gate evaluation could not be computed for this input."}
