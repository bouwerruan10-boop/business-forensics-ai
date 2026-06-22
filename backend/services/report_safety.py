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


def normalize_report(report) -> dict:
    """Return a render-safe copy of ``report`` (always a dict; no None/wrong-typed containers)."""
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
    return r
