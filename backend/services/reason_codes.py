"""
Imara Score reason codes (explainability).

Credit-decision practice (ECOA/Reg B adverse-action; FICO/VantageScore "score
factors") requires the principal reasons a score isn't higher, listed in order
of impact, and consistent with the ACTUAL model. This derives those reasons
deterministically from Imara's own weighted components — `weight x (100 - value)`
is exactly how much each component holds the score back — and ties each to the
concrete underlying number. No LLM, no surrogate: it reflects the real scoring
math. Decision-support, not a credit decision under the NCA.
"""


def _num(d, k, default=None):
    v = (d or {}).get(k)
    return v if isinstance(v, (int, float)) else default


def _driver_for(label, report):
    """A concrete, specific driver string for a component, from the report."""
    ratios = report.get("financial_ratios") or {}

    def rv(key):
        r = ratios.get(key) or {}
        return r.get("value"), r.get("benchmark")

    if label == "Profitability":
        nm, nb = rv("net_margin"); gm, gb = rv("gross_margin")
        if nm is not None:
            return "Net margin {:.1f}%{}".format(nm, " vs sector {:.1f}%".format(nb) if isinstance(nb, (int, float)) else "")
        if gm is not None:
            return "Gross margin {:.1f}%{}".format(gm, " vs sector {:.1f}%".format(gb) if isinstance(gb, (int, float)) else "")
        return "Earnings quality"
    if label == "Credit Readiness":
        g = report.get("credit_grade"); cs = report.get("credit_score")
        return "Credit grade {}{}".format(g or "n/a", " (score {})".format(cs) if cs else "")
    if label == "Risk & Compliance":
        return "Risk findings across the analysis"
    if label == "Operational Efficiency":
        dd, db = rv("debtor_days")
        if dd is not None:
            return "Debtor days {:.0f}{}".format(dd, " vs sector {:.0f}".format(db) if isinstance(db, (int, float)) else "")
        return "Operational throughput"
    if label == "Financial Integrity":
        lvl = report.get("fraud_risk_level")
        return "Fraud/anomaly risk {}".format(lvl or "assessed")
    if label == "Market Visibility":
        return report.get("market_context_summary") or "Market presence and visibility"
    if label == "Tax Compliance":
        return report.get("sa_tax_summary") or "SARS tax compliance"
    if label == "Legal Compliance":
        return report.get("sa_legal_summary") or "Companies Act / CIPC / BBBEE compliance"
    return label


def reason_codes(report: dict, top_n: int = 4) -> dict:
    """Ordered principal reasons the score isn't higher, plus top strengths."""
    comps = report.get("imara_components") or []
    score = report.get("imara_score")
    if not comps:
        return {"score": score, "band": report.get("imara_band"), "reasons": [], "strengths": [],
                "available": False}

    enriched = []
    for c in comps:
        w = float(c.get("weight") or 0)
        v = max(0.0, min(100.0, float(c.get("value") or 0)))
        enriched.append({
            "factor": c.get("label"), "score": round(v), "weight": round(w, 3),
            "_shortfall": w * (100 - v), "_strength": w * v,
        })

    reasons = sorted(enriched, key=lambda x: -x["_shortfall"])
    strengths = sorted(enriched, key=lambda x: -x["_strength"])

    out_reasons = []
    for r in reasons[:top_n]:
        if r["_shortfall"] <= 0.5:   # near-perfect component — not a real drag
            continue
        out_reasons.append({
            "factor": r["factor"], "score": r["score"],
            "impact": round(r["_shortfall"], 1),
            "detail": _driver_for(r["factor"], report),
        })
    out_strengths = [{"factor": s["factor"], "score": s["score"]} for s in strengths[:3] if s["score"] >= 55]

    return {
        "score": score, "band": report.get("imara_band"), "available": True,
        "reasons": out_reasons, "strengths": out_strengths,
        "disclaimer": ("Principal factors affecting the Imara Score, ordered by impact, derived directly from the "
                       "score's own weighted components. Decision-support — not a credit decision or adverse-action "
                       "notice under the National Credit Act."),
    }
