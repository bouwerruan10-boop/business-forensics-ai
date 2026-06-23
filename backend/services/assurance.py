"""
Assurance & statutory-compliance recommender — DETERMINISTIC (no LLM).

Two SA-statutory facts most SMEs get wrong and overpay for, computed by arithmetic
from data Imara already ingests:

1. Public Interest Score (PIS) -> the correct assurance tier.
   Companies Act 71/2008, Regulations 26 & 28. PIS = sum of:
     - 1 point per average number of employees during the year
     - 1 point per R1,000,000 (or part thereof) of third-party liabilities at year-end
     - 1 point per R1,000,000 (or part thereof) of turnover during the year
     - 1 point per individual with a beneficial interest in the company's securities
   Tier:
     - Public / state-owned company .......................... AUDIT (always)
     - PIS >= 350 ............................................ AUDIT
     - PIS 100-349, financials compiled INTERNALLY ........... AUDIT
     - PIS 100-349, financials compiled INDEPENDENTLY ........ INDEPENDENT REVIEW
     - PIS < 100 ............................................. INDEPENDENT REVIEW
     - OWNER-MANAGED (every shareholder is a director) ....... EXEMPT -> COMPILATION only
       (s30(2A); unless a mandatory-audit category applies)
   Many small owner-managed Pty Ltds therefore need ONLY a compilation and are
   paying R15k-R50k for an audit they don't need. This is a pure cost-saving finding.

2. CIPC standing awareness (annual return + beneficial-ownership register).
   We cannot see live CIPC status from a document, so this is an AWARENESS/RISK flag,
   never a fabricated "deregistered" status: a company that misses 2 consecutive annual
   returns is deregistered by CIPC and becomes un-bankable. BO register has been
   mandatory with the annual return since 1 July 2024.

Indicative SA assurance costs (sourced ranges, flagged indicative):
    audit R15,000-R50,000 | independent review ~R8,000-R25,000 | compilation bundled.
"""
import math
import re
from datetime import date

# Indicative SA cost ranges (ZAR) — for the cost-saving narrative only.
COST = {
    "audit": (15000, 50000),
    "independent review": (8000, 25000),
    "compilation": (0, 0),
}

_PUBLIC_HINTS = ("public", "soc", "state-owned", "state owned", "ltd)")  # 'Ltd)' = public Ltd, not (Pty) Ltd


def _n(v):
    """Defensive numeric coercion (handles '1,000', 'R 1 000', None, junk)."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").replace(" ", "").replace("R", "").replace("$", ""))
    except (ValueError, TypeError):
        return None


def _is_public(entity_type: str) -> bool:
    e = (entity_type or "").lower()
    if "(pty)" in e or "pty ltd" in e or "private" in e:
        return False
    return any(h in e for h in _PUBLIC_HINTS)


def public_interest_score(headcount=0, annual_revenue=0, third_party_liabilities=None,
                          beneficial_owners=None) -> dict:
    """Compute the PIS and its component breakdown. 'or part thereof' -> round up."""
    emp = int(round(_n(headcount) or 0))
    rev = _n(annual_revenue) or 0.0
    tpl = _n(third_party_liabilities)
    bo = beneficial_owners if isinstance(beneficial_owners, int) and beneficial_owners >= 0 else None

    emp_pts = max(emp, 0)
    rev_pts = math.ceil(rev / 1_000_000) if rev > 0 else 0
    tpl_pts = math.ceil(tpl / 1_000_000) if (tpl and tpl > 0) else 0
    bo_pts = bo if bo is not None else 0

    pis = emp_pts + rev_pts + tpl_pts + bo_pts
    return {
        "pis": pis,
        "bo_known": bo is not None,
        "tpl_known": tpl is not None,
        "components": {
            "employees": emp_pts,
            "turnover_Rm": rev_pts,
            "third_party_liabilities_Rm": tpl_pts,
            "beneficial_owners": bo_pts,
        },
        "note": ("PIS is a lower bound — add 1 point per shareholder (beneficial owner); "
                 "this rarely changes the tier." if bo is None else ""),
    }


def assess(headcount=0, annual_revenue=0, financial_figures=None, entity_type="",
           cipc_number="", beneficial_owners=None) -> dict:
    """Top-level: PIS + assurance-tier recommendation + CIPC awareness. Pure; never raises."""
    figs = financial_figures or {}
    rev = _n(annual_revenue) or _n(figs.get("revenue")) or 0.0
    tpl = _n(figs.get("total_liabilities"))
    emp = int(round(_n(headcount) or 0))

    if rev <= 0 and emp <= 0:
        return {"available": False,
                "reason": "Needs headcount and/or turnover to compute the Public Interest Score."}

    pis_block = public_interest_score(emp, rev, tpl, beneficial_owners)
    pis = pis_block["pis"]
    public = _is_public(entity_type)

    # --- Determine the assurance tier ---
    notes = []
    if public:
        tier, firm = "audit", True
        reason = "Public / state-owned companies must be audited regardless of Public Interest Score."
    elif pis >= 350:
        tier, firm = "audit", True
        reason = "PIS of {} is >= 350 -> a statutory audit is required.".format(pis)
    elif pis >= 100:
        tier, firm = "independent review", False
        reason = ("PIS of {} is in the 100-349 band. If your financials are compiled INDEPENDENTLY "
                  "(by an outside accountant) an independent review suffices; if compiled INTERNALLY, "
                  "an audit is required.").format(pis)
        notes.append("Becomes a full AUDIT if the statements are prepared internally (in-house).")
    else:
        tier, firm = "independent review", False
        reason = "PIS of {} is below 100 -> an independent review (not a full audit) is the default.".format(pis)

    # Owner-managed exemption (s30(2A)) — only when no mandatory-audit category applies.
    owner_managed_exempt = not (public or pis >= 350)
    if owner_managed_exempt:
        notes.append("OWNER-MANAGED EXEMPTION: if every shareholder is also a director, the company is "
                     "exempt from BOTH audit and independent review (Companies Act s30(2A)) — only a "
                     "compilation is required. Confirm your shareholder/director overlap.")

    lo, hi = COST.get(tier, (0, 0))
    saving = None
    if tier != "audit":
        a_lo, a_hi = COST["audit"]
        saving = "Avoids an unnecessary audit (~R{:,}-R{:,}) if you do not fall in a mandatory-audit category.".format(a_lo, a_hi)

    assurance = {
        "available": True,
        "public_interest_score": pis,
        "pis_breakdown": pis_block["components"],
        "pis_note": pis_block["note"],
        "recommended_tier": tier,
        "is_mandatory": firm,
        "reasoning": reason,
        "notes": notes,
        "indicative_cost_zar": {"low": lo, "high": hi} if (lo or hi) else None,
        "potential_saving": saving,
        "disclaimer": ("Indicative guidance from the Public Interest Score (Companies Act Reg 26/28), "
                       "not a legal determination. A mandatory-audit category (e.g. holding >R5m in a "
                       "fiduciary capacity, or an MOI requirement) overrides this. Confirm with a "
                       "registered accountant/auditor before changing your assurance engagement."),
        "cipc": cipc_compliance(cipc_number, entity_type),
    }
    return assurance


def cipc_compliance(cipc_number="", entity_type="") -> dict:
    """CIPC annual-return + beneficial-ownership AWARENESS (not a verified status)."""
    num = (cipc_number or "").strip()
    m = re.match(r"^\s*(\d{4})\s*/\s*(\d+)\s*/\s*(\d{2})\s*$", num)
    if not m:
        return {
            "number_provided": bool(num),
            "valid_format": False,
            "flag": ("No valid CIPC registration number on file. Confirm the company is CIPC-registered "
                     "and in good standing — lenders and funders will not transact with an unregistered "
                     "or deregistered entity." if not num else
                     "CIPC number format looks unusual (expected YYYY/NNNNNN/NN). Verify it."),
            "obligations": _CIPC_OBLIGATIONS,
        }
    reg_year = int(m.group(1))
    age = max(date.today().year - reg_year, 0)
    return {
        "number_provided": True,
        "valid_format": True,
        "registration_year": reg_year,
        "age_years": age,
        "flag": ("Verify your CIPC annual return and beneficial-ownership filing are up to date. "
                 "Two consecutive missed annual returns trigger CIPC deregistration — a deregistered "
                 "company cannot trade, contract or bank, making it un-fundable."),
        "obligations": _CIPC_OBLIGATIONS,
    }


_CIPC_OBLIGATIONS = [
    "File the CIPC annual return every year (within 30 business days of the incorporation anniversary).",
    "File the beneficial-ownership register with/before the annual return (mandatory since 1 July 2024).",
    "Keep MOI, directors and registered address current at CIPC.",
]
