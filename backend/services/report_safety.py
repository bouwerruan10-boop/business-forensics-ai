"""
report_safety.py - defensive normaliser run at the entry of the HTML/PDF report
renderers. The live pipeline always builds well-typed report dicts, but a corrupted
or old-schema record loaded from the DB could carry a None-valued or wrong-typed
field (e.g. ``scores: None``). ``dict.get(k, default)`` returns the *stored* None in
that case, not the default, which then crashes a downstream ``.get``/iteration.

This normaliser makes the renderers total: strip None-valued keys (so ``.get``
defaults apply) and coerce the known container fields to the right empty type.
Pure; never raises.
"""

# Fields the renderers access as dicts (``.items()`` / chained ``.get``).
_DICT_FIELDS = {
    "scores", "financial_ratios", "financial_figures", "department_findings",
    "tax_optimization", "tax_risk_flags", "faithfulness_summary", "prose_verifier_summary",
    "normalization", "lender_view", "funding_fit", "cross_agent_consistency",
    "supplier_benchmark", "bank_signals", "distress_score", "cashflow_13week",
    "audit", "decision_support", "llm_usage", "document_coverage",
}

# Fields the renderers iterate as lists.
_LIST_FIELDS = {
    "all_findings_ranked", "quick_wins", "implementation_roadmap", "top_priority_issues",
    "systemic_themes", "imara_components", "forecast_monthly", "forecast_assumptions",
    "fraud_indicators", "credit_barriers", "credit_strengths", "credit_products",
    "key_risks", "key_opportunities", "market_news", "market_competitors",
    "market_opportunities", "market_risks", "agent_timings", "critical_findings_list",
}

# List fields whose elements the renderers access as dicts (``elem.get(...)``).
# A junk element (None / int / str) would crash that access, so filter to dicts.
_LIST_OF_DICT_FIELDS = {
    "imara_components", "all_findings_ranked", "quick_wins", "implementation_roadmap",
    "top_priority_issues", "forecast_monthly", "market_competitors", "critical_findings_list",
}

# Scalar fields the renderers compare (``>=``) or do arithmetic on — must be real numbers.
_NUM_FIELDS = {
    "imara_score", "credit_score", "valuation_low", "valuation_mid", "valuation_high",
    "forecast_base_12m", "forecast_bull_12m", "forecast_bear_12m", "annual_revenue", "headcount",
}


def _as_number(v):
    """Return v as a finite number, or None if it cannot be one (str digits coerce; junk drops)."""
    import math
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v if math.isfinite(v) else None
    if isinstance(v, str):
        try:
            n = float(v.strip().replace(",", ""))
            return n if math.isfinite(n) else None
        except (ValueError, AttributeError):
            return None
    return None


def normalize_report(report) -> dict:
    """Return a render-safe copy of ``report`` (always a dict; no None/wrong-typed containers,
    no junk list elements, no non-numeric scalars where the renderers expect numbers)."""
    if not isinstance(report, dict):
        return {}
    r = dict(report)
    # Drop None-valued keys so `.get(k, default)` falls back to the default.
    for k in [k for k, v in r.items() if v is None]:
        del r[k]
    # Coerce known container fields that are present but the wrong type.
    for k in _DICT_FIELDS:
        if k in r and not isinstance(r[k], dict):
            r[k] = {}
    for k in _LIST_FIELDS:
        if k in r and not isinstance(r[k], list):
            r[k] = []
    # Drop non-dict elements from list-of-dict fields (renderers call elem.get()).
    for k in _LIST_OF_DICT_FIELDS:
        if isinstance(r.get(k), list):
            r[k] = [e for e in r[k] if isinstance(e, dict)]
    # Score components feed round()/arithmetic on value+weight — keep those numeric or absent.
    # Rebuild with copies (shallow r=dict(report) shares the nested dicts) so we never mutate caller state.
    if isinstance(r.get("imara_components"), list):
        comps = []
        for c in r["imara_components"]:
            c = dict(c)
            for nk in ("value", "weight"):
                if nk in c:
                    n = _as_number(c[nk])
                    if n is None:
                        del c[nk]
                    else:
                        c[nk] = n
            comps.append(c)
        r["imara_components"] = comps
    # Coerce numeric scalar fields; drop (use default) if not number-able.
    for k in _NUM_FIELDS:
        if k in r:
            n = _as_number(r[k])
            if n is None:
                del r[k]
            else:
                r[k] = n
    # Sanitise nested numeric ratio values so a bad value/benchmark can't crash arithmetic.
    fr = r.get("financial_ratios")
    if isinstance(fr, dict):
        clean = {}
        for key, entry in fr.items():
            if not isinstance(entry, dict):
                continue
            e = dict(entry)
            for nk in ("value", "benchmark"):
                if nk in e:
                    n = _as_number(e[nk])
                    if n is None:
                        del e[nk]
                    else:
                        e[nk] = n
            clean[key] = e
        r["financial_ratios"] = clean
    return r
