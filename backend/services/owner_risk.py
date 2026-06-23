"""
Owner-level risk dimension — deterministic, decision-support.

SA SME lending is BLENDED: lenders assess the owner alongside the business
because almost every SME facility requires a PERSONAL SURETY from each
director/shareholder (jointly & severally), and lenders pull BOTH the business
AND the owner's personal credit + court judgments (sources: SME South Africa
loan-requirements guide; Finfind "understanding personal surety"; NCA
reckless-credit / over-indebtedness provisions). Imara historically scored the
BUSINESS only — this module surfaces the owner-exposure blind spot.

It is built only from the business's own records (entity type, headcount,
director's-loan flag, owner add-backs, the lender-view decline verdict) plus the
structural fact that SA SME debt is personally guaranteed. It NEVER invents the
owner's personal credit data — what it cannot see, it lists as a DATA GAP.

Everything here is INDICATIVE decision-support. It is NOT an NCA credit
decision, NOT a personal credit-bureau assessment, and NOT advice, and it is NOT
an Imara Score input (consistent with the FAIS/NCA framing across Imara).
"""

__all__ = ["analyze_owner_risk"]

_SURETY_WORDS = (
    "suretyship", "surety", "personal guarantee", "personal guaranty",
    "jointly and severally", "deed of suretyship", "personal liability",
)
_LOAN_ACCT_WORDS = ("loan account", "director's loan", "directors loan",
                    "shareholder loan", "members loan", "member's loan")

_SOLE_WORDS = ("sole prop", "sole proprietor", "sole trader", "proprietor")


def _d(x):
    return x if isinstance(x, dict) else {}


def _l(x):
    return x if isinstance(x, list) else []


def _txt(x):
    try:
        return str(x) if x is not None else ""
    except Exception:
        return ""


def _has(text, words):
    t = _txt(text).lower()
    return any(w in t for w in words)


def _int(v):
    try:
        n = int(float(v))
        return n if n >= 0 else 0
    except (TypeError, ValueError):
        return 0


_LEVELS = (("high", 75), ("elevated", 50), ("moderate", 25), ("low", 0))


def _level(score):
    for name, floor in _LEVELS:
        if score >= floor:
            return name
    return "low"


def analyze_owner_risk(report, profile=None, legal_text="", financial_text=""):
    """Blend the owner's likely personal exposure with the business's own risk.

    Returns a structured, JSON-safe dict. Robust to malformed / hostile input.
    """
    try:
        report = _d(report)
        profile = _d(profile)
        legal_text = _txt(legal_text)
        financial_text = _txt(financial_text)

        entity = (_txt(profile.get("entity_type")) or _txt(report.get("entity_type"))).lower()
        headcount = _int(profile.get("headcount") if profile.get("headcount") not in (None, "") else report.get("headcount"))

        norm = _d(report.get("normalization"))
        lender = _d(report.get("lender_view"))
        loan_flag = _d(norm.get("loan_account_flag"))
        add_backs = _l(norm.get("add_backs"))
        decline_risk = _txt(lender.get("decline_risk")).lower()

        factors = []
        score = 0

        # 1) Personal surety exposure — the defining owner risk in SA SME lending.
        surety_seen = _has(legal_text, _SURETY_WORDS)
        if surety_seen:
            score += 30
            factors.append({
                "severity": "high",
                "title": "Personal surety in play",
                "detail": ("Suretyship / personal-guarantee language appears in the uploaded documents. SA SME "
                           "facilities are typically signed jointly & severally, so the owner's PERSONAL estate "
                           "(home, savings) backs the business debt — a default reaches the owner personally."),
                "what_to_fix": ("Quantify the total surety exposure across all facilities, confirm whether it is "
                                "joint & several, and seek to cap or release surety as the balance sheet strengthens."),
            })
        else:
            score += 15
            factors.append({
                "severity": "medium",
                "title": "Personal surety likely required (not yet evidenced)",
                "detail": ("No suretyship document was provided, but most SA SME lenders require a personal surety "
                           "from every director/shareholder. Assume the owner's personal estate is on the line until "
                           "proven otherwise."),
                "what_to_fix": "Provide existing surety agreements so the real personal exposure can be assessed.",
            })

        # 2) Sole proprietor / unlimited personal liability.
        if _has(entity, _SOLE_WORDS):
            score += 20
            factors.append({
                "severity": "high",
                "title": "No legal separation (sole proprietor)",
                "detail": ("As a sole proprietor there is no separation between the owner and the business — ALL "
                           "business debt is automatically the owner's personal debt, with no surety even needed."),
                "what_to_fix": "Consider incorporating (Pty Ltd) to separate personal and business liability before scaling debt.",
            })

        # 3) Owner / key-person concentration.
        if 0 < headcount <= 5 or _has(entity, _SOLE_WORDS) or _has(entity, ("cc", "close corporation")):
            score += 15
            factors.append({
                "severity": "medium",
                "title": "Owner / key-person concentration",
                "detail": ("A very small team or owner-managed structure means the business depends on one person. "
                           "If the owner is incapacitated, debt service and operations are at immediate risk — a "
                           "concern lenders price in."),
                "what_to_fix": "Key-person life/disability cover ceded to the lender, plus a documented second signatory / succession.",
            })

        # 4) Director's loan account — commingling + a soft asset.
        if loan_flag.get("flagged") or _has(financial_text, _LOAN_ACCT_WORDS):
            score += 18
            factors.append({
                "severity": "medium",
                "title": "Director's / shareholder loan account active",
                "detail": ("Owner drawings run through a loan account rather than salary. This commingles personal "
                           "and business cash, can trigger SARS s7C/s8F treatment, and the balance is an asset the "
                           "business may struggle to recover — all of which weaken the owner-business separation."),
                "what_to_fix": "Formalise owner remuneration as salary/dividends and document any loan account on written terms.",
            })

        # 5) Owner add-backs / commingling found during normalisation.
        if add_backs:
            score += 10
            factors.append({
                "severity": "low",
                "title": "Personal / owner items mixed into the accounts",
                "detail": ("Owner or one-off items were added back when normalising earnings, indicating personal and "
                           "business expenses are intermingled — this reduces the reliability of the books a lender relies on."),
                "what_to_fix": "Run personal expenses through personal accounts; keep the business books clean.",
            })

        # 6) Blended distress — a shaky business + a personal surety lands on the owner.
        if decline_risk in ("high", "elevated") and (surety_seen or _has(entity, _SOLE_WORDS)):
            score += 25
            factors.append({
                "severity": "high",
                "title": "Business stress flows through to the owner personally",
                "detail": ("The lender-view decline risk is " + decline_risk + " AND the owner carries personal "
                           "liability — so weakness in the business converts directly into personal financial risk "
                           "for the owner, not just a corporate loss."),
                "what_to_fix": "Treat business turnaround as personal risk management; do not add further personally-guaranteed debt while stressed.",
            })

        score = max(0, min(100, int(round(score))))

        data_gaps = [
            "Owner's personal credit-bureau score and any court judgments / defaults (lenders pull this alongside the business).",
            "Owner's personal balance sheet / net worth that actually backs the surety.",
            "Other sureties the owner has already signed elsewhere (contingent personal liabilities).",
            "Personal living expenses for an NCA-style affordability / over-indebtedness check.",
        ]

        return {
            "available": True,
            "owner_risk_score": score,
            "owner_risk_level": _level(score),
            "factors": factors,
            "data_gaps": data_gaps,
            "summary": ("Indicative owner-level (personal) risk is " + _level(score) + " (" + str(score) +
                        "/100), reflecting the SA reality that the owner personally guarantees SME debt. "
                        "A licensed credit provider must confirm with the owner's actual personal credit + net worth."),
            "is_not": "an NCA credit decision, a personal credit-bureau assessment, or financial advice",
            "disclaimer": ("Decision-support only: a blended owner+business risk VIEW built from the business's own "
                           "records and the SA SME lending reality that owners sign personal surety. Higher score = "
                           "more owner exposure. It is NOT an NCA credit decision, NOT a personal credit-bureau "
                           "assessment, and NOT advice; the owner's actual personal credit, net worth and existing "
                           "sureties must be assessed by a licensed credit provider."),
        }
    except Exception:
        return {"available": False, "reason": "Owner-risk view could not be computed for this input."}
