"""
Insurance + cession fundability check — deterministic, decision-support.

In SA, security over an insurance policy is taken by CESSION (the policyholder
cedes the policy / its proceeds to the lender; on death/default the lender
claims the benefit). Lenders routinely require, and take cession of:
  - KEY-PERSON life & disability cover (the owner the business depends on),
  - CREDIT-LIFE / loan-protection cover (settles the outstanding balance),
  - ASSET cover on pledged property/plant/equipment (lender as cessionary /
    loss-payee), and
  - BUSINESS-INTERRUPTION cover (protects cash-flow / debt service if operations
    halt).
(Sources: Practical Law "Lending and Taking Security in South Africa"; Momentum/
Old Mutual key-person assurance; SME South Africa funding guides.)

Imara scored neither the owner's nor the firm's insurance posture. This module
surfaces, from the business's own records, which covers a lender will expect, any
EVIDENCE of them, whether they appear CEDED as security, and the DATA GAPS it
cannot see (policy schedules, sums insured, cession agreements). It NEVER invents
a policy.

Decision-support only. NOT financial/insurance advice (FAIS s1(3)(a) objective-
information exemption), NOT a recommendation of any product, and NOT an Imara
Score input.
"""

__all__ = ["assess_insurance_cession"]

_KEY_PERSON = ("key man", "keyman", "key person", "key-person", "key individual")
_CREDIT_LIFE = ("credit life", "loan protection", "loan cover", "credit protection", "loan insurance")
_BI = ("business interruption", "loss of profits", "loss of income", "loss of revenue")
_ASSET_COVER = ("asset insurance", "property insurance", "plant and machinery", "equipment insurance",
                "fire and allied", "sasria", "short-term insurance", "business insurance", "asset cover")
_GENERIC_INS = ("insurance", "insurer", "policy", "premium", "cover", "assurance")
_CESSION = ("cession", "ceded", "cede ", "cessionary", "loss payee", "loss-payee",
            "collateral assignment", "security cession", "ceded as security")
_SOLE = ("sole prop", "sole proprietor", "sole trader", "proprietor")


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
        return 0.0
    import math
    return f if math.isfinite(f) and f > 0 else 0.0


def _has(text, words):
    t = _txt(text).lower()
    return any(w in t for w in words)


def _int(v):
    try:
        n = int(float(v))
        return n if n >= 0 else 0
    except (TypeError, ValueError):
        return 0


def assess_insurance_cession(report, profile=None, financial_text="", legal_text=""):
    """Lender-readiness of the firm's insurance + cession posture. JSON-safe, hostile-input-proof."""
    try:
        report = _d(report)
        profile = _d(profile)
        text = (_txt(financial_text) + "\n" + _txt(legal_text)).lower()

        figs = _d(report.get("financial_figures"))
        entity = (_txt(profile.get("entity_type")) or _txt(report.get("entity_type"))).lower()
        headcount = _int(profile.get("headcount") if profile.get("headcount") not in (None, "") else report.get("headcount"))
        debt = _num(figs.get("total_debt"))
        total_assets = _num(figs.get("total_assets"))
        current_assets = _num(figs.get("current_assets"))
        fixed_assets = max(0.0, total_assets - current_assets)

        owner_dependent = (0 < headcount <= 10) or _has(entity, _SOLE) or not headcount
        ceded = _has(text, _CESSION)

        covers = []

        def add(cover, relevant, why, evidence, ceded_status, action):
            covers.append({
                "cover": cover, "relevant": relevant, "why_lender_wants_it": why,
                "evidence": evidence,            # present | none | unknown
                "cession_status": ceded_status,  # ceded | not_ceded | n/a | unknown
                "action": action,
            })

        # 1) Key-person life & disability
        kp_seen = _has(text, _KEY_PERSON)
        add("Key-person life & disability cover",
            bool(owner_dependent),
            "The business depends on the owner/a key individual; a lender wants the loan protected (and ceded to it) if that person dies or is disabled.",
            "present" if kp_seen else "none",
            ("ceded" if ceded else "not_ceded") if kp_seen else "unknown",
            "Take out key-person cover on the owner and cede it to the lender." if not kp_seen else
            ("Confirm the policy is ceded to the lender as security." if not ceded else "In place and ceded — keep the sum insured aligned to the debt."))

        # 2) Credit life / loan protection
        cl_seen = _has(text, _CREDIT_LIFE)
        add("Credit life / loan-protection cover",
            debt > 0,
            "Settles the outstanding loan balance on the owner's death or disability — many SA lenders require it on SME facilities.",
            "present" if cl_seen else "none",
            ("ceded" if ceded else "not_ceded") if cl_seen else "unknown",
            "Arrange credit-life cover sized to the facility." if not cl_seen else "Confirm it tracks the outstanding balance.")

        # 3) Asset cover on pledged security
        asset_seen = _has(text, _ASSET_COVER) or (_has(text, _GENERIC_INS) and not (kp_seen or cl_seen))
        add("Asset cover (property / plant / equipment)",
            fixed_assets > 0 or _has(text, _ASSET_COVER),
            "Any asset pledged as security must be insured, typically with the lender noted as cessionary / loss-payee.",
            "present" if asset_seen else "none",
            ("ceded" if ceded else "not_ceded") if asset_seen else "unknown",
            "Insure pledged assets and note the lender as loss-payee / cessionary." if not asset_seen else
            ("Add the lender as cessionary / loss-payee." if not ceded else "In place with the lender noted."))

        # 4) Business interruption
        bi_seen = _has(text, _BI)
        add("Business-interruption cover",
            True,
            "Protects cash-flow (and therefore debt service) if a disaster halts trading — strengthens the affordability case.",
            "present" if bi_seen else "none",
            "n/a", "Consider BI cover so debt service survives a trading interruption." if not bi_seen else "In place — confirm the indemnity period.")

        relevant = [c for c in covers if c["relevant"]]
        with_evidence = [c for c in relevant if c["evidence"] == "present"]
        gaps = [c for c in relevant if c["evidence"] == "none"]
        ceded_ct = sum(1 for c in relevant if c["cession_status"] == "ceded")

        if relevant and len(with_evidence) == len(relevant) and ceded_ct >= 1:
            readiness = "strong"
        elif with_evidence:
            readiness = "partial"
        else:
            readiness = "low"

        data_gaps = [
            "Actual policy schedules + sums insured (is cover adequate vs the debt and asset values?).",
            "Signed cession / collateral-assignment agreements in favour of the lender.",
            "Beneficiary / loss-payee nominations on each policy.",
            "Disability + key-person definitions and any exclusions a lender would scrutinise.",
        ]

        return {
            "available": True,
            "readiness": readiness,
            "covers": covers,
            "relevant_count": len(relevant),
            "evidenced_count": len(with_evidence),
            "gaps_count": len(gaps),
            "ceded_observed": bool(ceded),
            "data_gaps": data_gaps,
            "summary": ("Insurance + cession readiness is " + readiness + ": " + str(len(with_evidence)) +
                        " of " + str(len(relevant)) + " lender-relevant covers show evidence in the documents" +
                        (" and a cession is referenced." if ceded else "; no cession to a lender was detected.")),
            "is_not": "financial or insurance advice, a recommendation of any insurance product, or an Imara Score input",
            "disclaimer": ("Decision-support only: which insurance covers a lender typically expects to be in place and "
                           "CEDED as security, checked against the business's own documents. It does NOT verify policies, "
                           "is NOT financial/insurance advice and NOT a product recommendation (objective information only), "
                           "and is NOT an Imara Score input. Confirm cover and cessions with a licensed broker/insurer."),
        }
    except Exception:
        return {"available": False, "reason": "Insurance/cession check could not be computed for this input."}
