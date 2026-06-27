"""
action_constraints.py - deterministic "what you can change vs what's fixed".

For each improvement action the simulator derives, attaches: a realistic
changeable share (reusing simulation._CLOSE_FRACTIONS), what is typically fixed,
and grounded do's / don'ts + a rough timeline. This is realistic-ceiling
decision-support; it does NOT change the Imara Score. No LLM.
"""

from services.simulation import derive_actions, _CLOSE_FRACTIONS

# Grounded, generic-but-true constraint profiles per action id.
_PROFILES = {
    "gross_margin": {
        "fixed": "Input/material costs and what the market will pay cap how far gross margin can move.",
        "dos": ["Renegotiate supplier pricing or consolidate volume", "Cut waste and shrinkage",
                "Shift the mix toward higher-margin lines"],
        "donts": ["Don't cut quality in a way that drives customers away",
                  "Don't raise price faster than the market will bear"],
        "timeline": "3-6 months",
    },
    "opex": {
        "fixed": "Some overheads are contractual (leases, salaries) and fixed for 6-12 months.",
        "dos": ["Review discretionary spend line by line", "Renegotiate recurring contracts",
                "Benchmark suppliers (bank charges, telecoms, insurance, software)"],
        "donts": ["Don't cut so deep you damage delivery or lose key staff"],
        "timeline": "1-6 months",
    },
    "debtor_days": {
        "fixed": "Existing customer contracts may lock in payment terms (e.g. 60 days).",
        "dos": ["Offer early-payment discounts", "Automate invoicing and reminders",
                "Tighten credit terms for new customers"],
        "donts": ["Don't breach existing contracts", "Don't push so hard you lose key accounts"],
        "timeline": "1-3 months",
    },
    "inventory_days": {
        "fixed": "A minimum safety stock is needed to avoid stockouts and lost sales.",
        "dos": ["Rationalise slow-moving SKUs", "Tighten reorder points with demand forecasting",
                "Negotiate consignment / just-in-time with suppliers"],
        "donts": ["Don't cut below safety stock for your lead times",
                  "Don't strand cash chasing volume discounts"],
        "timeline": "3-6 months",
    },
    "revenue_growth": {
        "fixed": "Market size and your delivery capacity cap how fast you can grow profitably.",
        "dos": ["Deepen share with existing customers", "Add adjacent products/services",
                "Improve conversion before adding spend"],
        "donts": ["Don't take on negative-margin work", "Don't outrun your working capital"],
        "timeline": "ongoing",
    },
    "price": {
        "fixed": "Customer price sensitivity and competitor pricing constrain increases.",
        "dos": ["Raise prices on low-sensitivity lines first", "Tie increases to a value/quality signal",
                "Test in segments before a blanket change"],
        "donts": ["Don't apply a blanket increase blind to elasticity", "Don't surprise key accounts"],
        "timeline": "1-3 months",
    },
    "supplier_switch": {
        "fixed": "Switching costs, contracts and service-equivalence limit how much you can move.",
        "dos": ["Switch the benchmarked categories first", "Run a structured RFQ"],
        "donts": ["Don't switch a critical supplier without a service guarantee",
                  "Don't ignore exit penalties"],
        "timeline": "1-3 months",
    },
}

_DEFAULT = {
    "fixed": "Real-world constraints limit how much of the theoretical gap is actually reachable.",
    "dos": ["Move the controllable drivers first", "Validate the change on a small scale before scaling"],
    "donts": ["Don't assume the full gap is achievable", "Don't break a working part of the business to chase it"],
    "timeline": "varies",
}


def annotate(report):
    """Return each derived action enriched with changeable-vs-fixed guidance."""
    try:
        actions = derive_actions(report if isinstance(report, dict) else {})
    except Exception:
        actions = []

    out = []
    for a in actions:
        if not isinstance(a, dict):
            continue
        aid = a.get("id")
        prof = _PROFILES.get(aid, _DEFAULT)
        frac = _CLOSE_FRACTIONS.get(aid)
        mx = a.get("max")
        realistic = round(mx * frac, 1) if (frac and isinstance(mx, (int, float))) else None
        out.append({
            "id": aid,
            "label": a.get("label"),
            "max": mx,
            "unit": a.get("unit"),
            "changeable_fraction": frac,
            "realistic_ceiling": realistic,
            "fixed": prof["fixed"],
            "dos": prof["dos"],
            "donts": prof["donts"],
            "timeline": prof["timeline"],
        })

    return {
        "actions": out,
        "count": len(out),
        "note": "Realistic-ceiling guidance for what's changeable vs fixed - it does not change the Imara Score.",
    }
