"""
applicability.py — deterministic data-sufficiency / business-type gates.

Several specialist agents carry benchmark suites that only make sense for a
particular kind of business (OEE for manufacturing, fleet metrics for transport)
or that need data Imara's document set never contains (CRM pipelines, ad-spend
analytics). Left ungated, the LLM tends to *infer* these metrics from absent
data and emit confident but fabricated findings.

This module gives each such agent a short, honest applicability note so it
quantifies only what the data supports and explicitly says "not assessable"
otherwise — the same discipline the Market agents already follow.
"""

_TRANSPORT = ("logistic", "transport", "courier", "freight", "fleet", "trucking",
              "haulage", "distribution", "delivery", "shipping", "cartage")
_MANUFACTURING = ("manufactur", "production", "factory", "plant", "fabricat",
                  "assembly", "processing", "mill", "foundry", "industrial")


def business_kind(memory) -> str:
    """Conservative classifier from the stated industry: transport / manufacturing / general."""
    ind = (str(getattr(memory, "industry", "") or "") + " " +
           str(getattr(memory, "industry_key", "") or "")).lower()
    if any(w in ind for w in _TRANSPORT):
        return "transport"
    if any(w in ind for w in _MANUFACTURING):
        return "manufacturing"
    return "general"


def _industry_label(memory) -> str:
    return (str(getattr(memory, "industry", "") or "").strip()
            or str(getattr(memory, "industry_key", "") or "").strip()
            or "unspecified")


def applicability_note(memory, agent: str) -> str:
    """Tailored applicability/data-sufficiency block for the given agent."""
    kind = business_kind(memory)
    ind = _industry_label(memory)

    if agent == "operations":
        if kind == "manufacturing":
            return ("APPLICABILITY: this is a manufacturing/asset-intensive business, so OEE, "
                    "throughput, capacity-utilisation and shift-variance metrics apply. Quantify "
                    "ONLY from data actually present; where a metric is not in the data, say "
                    "\"not assessable from the supplied data\" rather than inventing a number.")
        return ("APPLICABILITY: the industry is \"%s\", which does NOT appear to be "
                "manufacturing/asset-intensive. OEE, throughput, capacity-utilisation, "
                "equipment-utilisation and shift-variance metrics likely DO NOT APPLY here - do "
                "NOT force them or fabricate equipment/production data. Focus on overhead "
                "efficiency, process cost and quality-cost findings the supplied data supports; "
                "if operational data is absent, say so explicitly." % ind)

    if agent == "logistics":
        if kind == "transport":
            return ("APPLICABILITY: this is a transport/distribution business, so fleet utilisation, "
                    "fuel-%, route/dead-kilometre and vehicle-downtime metrics apply. Quantify ONLY "
                    "from data present; otherwise say \"not assessable from the supplied data\".")
        return ("APPLICABILITY: the industry is \"%s\", which does NOT appear to be a "
                "transport/fleet/distribution business. Fleet utilisation, fuel-as-%%-of-revenue, "
                "dead-kilometres and vehicle-downtime metrics DO NOT APPLY - do NOT fabricate fleet "
                "or fuel figures. Raise a logistics finding ONLY if the data clearly evidences a "
                "fleet/distribution operation; otherwise report that fleet analysis is not "
                "applicable to this business." % ind)

    if agent == "sales":
        return ("DATA SUFFICIENCY: Imara's document set does not include CRM or pipeline exports. "
                "Win rate, pipeline velocity, average deal size, lead-to-customer conversion and "
                "LTV:CAC CANNOT be computed from financial statements alone - for any such metric, "
                "state \"not assessable from the supplied documents\" instead of inferring a figure. "
                "You MAY quantify revenue concentration (top-customer %), revenue per head and "
                "pricing/discount issues where the financial data supports them.")

    if agent == "marketing":
        return ("DATA SUFFICIENCY: Imara's document set does not include marketing-analytics, "
                "ad-spend or channel data. ROAS, CAC, CAC-payback, email open rates and "
                "conversion rates CANNOT be computed here - for any such metric, state "
                "\"not assessable from the supplied documents\" instead of inventing one. You MAY "
                "comment on marketing/advertising spend if it appears as a line item in the "
                "financials, and on online presence using the market-intelligence summary if present.")

    return ""
