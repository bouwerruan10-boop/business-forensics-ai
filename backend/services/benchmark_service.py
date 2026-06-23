"""
Benchmark Intelligence Service
Matches a business to the closest industry benchmark profile,
then provides comparison utilities used by all specialist agents.
African market profiles: South Africa, Nigeria, Kenya, Zimbabwe.
"""

import json
import os
from typing import Optional

_BENCHMARKS: dict = {}

def _load():
    global _BENCHMARKS
    if not _BENCHMARKS:
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'benchmarks.json')
        with open(path, 'r') as f:
            _BENCHMARKS = json.load(f)
    return _BENCHMARKS


# African country -> benchmark key mapping
_COUNTRY_PROFILE_MAP = {
    'south africa': 'south_africa_sme',
    'sa':           'south_africa_sme',
    'nigeria':      'nigeria_general',
    'kenya':        'kenya_general',
    'zimbabwe':     'zimbabwe_general',
}

# These keys are excluded from keyword-based industry scanning
_COUNTRY_PROFILE_KEYS = set(_COUNTRY_PROFILE_MAP.values())


def detect_industry(business_name: str = '', industry_hint: str = '',
                    file_names=None, data_keys=None,
                    country: str = '') -> str:
    """
    Return the best-matching industry key from benchmarks.json.
    Checks specific industry keywords first. If no match, falls back
    to an African country profile based on the country field.
    """
    file_names = file_names or []
    data_keys  = data_keys  or []
    data = _load()
    text = ' '.join([business_name, industry_hint, *file_names, *data_keys]).lower()
    country_lower = country.lower().strip()

    best_key = 'general'
    best_score = 0

    for key, industry in data['industries'].items():
        # Skip the fallback and African country overrides in keyword scan
        if key == 'general' or key in _COUNTRY_PROFILE_KEYS:
            continue
        score = sum(1 for kw in industry.get('keywords', []) if kw in text)
        if score > best_score:
            best_score = score
            best_key = key

    # If no specific industry matched, check for African country
    if best_score == 0 and country_lower:
        for country_kw, profile_key in _COUNTRY_PROFILE_MAP.items():
            if country_kw in country_lower:
                best_key = profile_key
                break

    return best_key


# Frontend dropdown values + common synonyms -> benchmark profile keys.
# Without this, keys like "retail" (frontend) silently miss "retail_general"
# (the actual profile) and fall back to the generic "general" benchmark.
_KEY_ALIASES = {
    "retail": "retail_general", "ecommerce": "retail_general", "e-commerce": "retail_general",
    "professional": "professional_services", "services": "professional_services",
    "consulting": "professional_services",
    "hospitality": "hospitality_restaurant", "tourism": "hospitality_restaurant",
    "hotel": "hotel_accommodation", "accommodation": "hotel_accommodation",
    "transport": "logistics_trucking", "logistics": "logistics_trucking",
    "technology": "technology_software", "tech": "technology_software", "software": "technology_software",
    "financial": "financial_services", "finance": "financial_services",
    "wholesale": "wholesale_distribution", "distribution": "wholesale_distribution",
    "property": "real_estate",
}


def resolve_benchmark_key(industry_key: str) -> str:
    """Map a raw industry key (frontend dropdown value, LLM hint, free text) to the best
    benchmark profile key. Fixes the silent 'general' fallback for keys that DO have a
    proper profile under a different name (e.g. 'retail' -> 'retail_general')."""
    industries = _load()['industries']
    key = str(industry_key or "").strip().lower()
    if not key:
        return "general"
    if key in industries:
        return key
    alias = _KEY_ALIASES.get(key)
    if alias and alias in industries:
        return alias
    detected = detect_industry(industry_hint=key)  # keyword scan for free-text / LLM keys
    if detected in industries and detected != "general":
        return detected
    return "general"


def get_benchmarks(industry_key: str) -> dict:
    """Return the full benchmark profile for an industry (resolving aliases / keywords)."""
    industries = _load()['industries']
    return industries.get(resolve_benchmark_key(industry_key), industries['general'])


def industry_display_name(industry_key: str) -> str:
    """Human-readable label for an industry key, from the resolved benchmark profile.
    Lets the report show 'Retail & E-commerce' instead of a raw key like 'retail_general'."""
    return get_benchmarks(industry_key).get("display_name") or "General Business"


def get_thresholds() -> dict:
    return _load().get('universal_thresholds', {})


def format_benchmark_context(industry_key: str,
                              annual_revenue: Optional[float] = None,
                              currency: str = 'USD') -> str:
    """
    Build a rich text block injected into every agent prompt.
    Gives agents the numbers they need to compare against.
    """
    bm = get_benchmarks(industry_key)
    name   = bm.get('display_name', 'General Business')
    m      = bm.get('margins', {})
    eff    = bm.get('efficiency', {})
    costs  = bm.get('cost_ratios', {})
    liq    = bm.get('liquidity', {})
    tq     = bm.get('top_quartile', {})
    notes  = bm.get('industry_notes', '')
    source = bm.get('_source', 'Damodaran NYU Stern, Jan 2026 + CFI')

    rev_context = ''
    if annual_revenue and annual_revenue > 0:
        rev_m = annual_revenue / 1_000_000
        rev_context = (
            "REVENUE-BASED IMPACT CALCULATOR (Annual Revenue: {} {:.1f}M):\n"
            "  * Each 1% gross margin improvement  = {} {:,.0f} additional profit\n"
            "  * Each 10 debtor days reduced       = {} {:,.0f} cash released\n"
            "  * Each 5% labour cost reduction     = {} {:,.0f} annual saving\n"
            "  * Each 1% EBITDA improvement        = {} {:,.0f} EBITDA uplift"
        ).format(
            currency, rev_m,
            currency, annual_revenue * 0.01,
            currency, annual_revenue / 365 * 10,
            currency, annual_revenue * 0.05,
            currency, annual_revenue * 0.01,
        )

    lines = [
        "INDUSTRY BENCHMARK PROFILE: {} (Source: {})".format(name, source),
        "",
        "MARGIN BENCHMARKS (industry medians):",
        "  * Gross Margin:        {:.1f}%   (Top quartile: {:.1f}%)".format(
            m.get('gross_margin', 0) * 100, tq.get('gross_margin', 0) * 100),
        "  * Operating Margin:    {:.1f}%   (Top quartile: {:.1f}%)".format(
            m.get('operating_margin', 0) * 100, tq.get('operating_margin', 0) * 100),
        "  * Net Margin:          {:.1f}%".format(m.get('net_margin', 0) * 100),
        "  * EBITDA Margin:       {:.1f}%".format(m.get('ebitda_margin', 0) * 100),
        "",
        "COST STRUCTURE BENCHMARKS:",
        "  * COGS % Revenue:      {:.1f}%".format(costs.get('cogs_pct_revenue', 0) * 100),
        "  * Labour % Revenue:    {:.1f}%  (Warning >40%, Critical >50%)".format(
            costs.get('labour_pct_revenue', 0) * 100),
    ]

    if costs.get('fuel_pct_revenue'):
        lines.append("  * Fuel % Revenue:      {:.1f}%".format(costs['fuel_pct_revenue'] * 100))
    if costs.get('fuel_diesel_pct_revenue'):
        lines.append("  * Diesel % Revenue:    {:.1f}%".format(costs['fuel_diesel_pct_revenue'] * 100))
    if costs.get('food_cost_pct'):
        lines.append("  * Food Cost %:         {:.1f}%".format(costs['food_cost_pct'] * 100))
    if costs.get('load_shedding_cost_pct'):
        lines.append("  * Load Shedding Cost:  {:.1f}%  (generator & downtime)".format(
            costs['load_shedding_cost_pct'] * 100))
    if costs.get('power_generator_pct_revenue'):
        lines.append("  * Power/Generator:     {:.1f}%".format(
            costs['power_generator_pct_revenue'] * 100))

    lines += [
        "",
        "EFFICIENCY BENCHMARKS:",
        "  * Debtor Days:         {} days  (Warning >50, Critical >70)".format(
            eff.get('debtor_days', 35)),
        "  * Creditor Days:       {} days".format(eff.get('creditor_days', 35)),
    ]
    if eff.get('inventory_turnover_days'):
        lines.append("  * Inventory Days:      {} days".format(eff['inventory_turnover_days']))
    if eff.get('fleet_utilisation_pct'):
        lines.append("  * Fleet Utilisation:   {:.0f}%  (Top quartile: {:.0f}%)".format(
            eff['fleet_utilisation_pct'] * 100, tq.get('fleet_utilisation_pct', 0.88) * 100))
    if eff.get('occupancy_rate'):
        lines.append("  * Occupancy Rate:      {:.0f}%  (Top quartile: {:.0f}%)".format(
            eff['occupancy_rate'] * 100, tq.get('occupancy_rate', 0) * 100))
    if eff.get('revenue_per_employee'):
        lines.append("  * Revenue/Employee:    {} {:,}".format(
            currency, eff['revenue_per_employee']))

    lines += [
        "",
        "LIQUIDITY BENCHMARKS:",
        "  * Current Ratio:       {:.1f}x  (Critical <0.8x)".format(liq.get('current_ratio', 1.5)),
        "  * Quick Ratio:         {:.1f}x".format(liq.get('quick_ratio', 1.0)),
    ]

    if notes:
        lines += ["", "INDUSTRY-SPECIFIC NOTES:", "  " + notes]

    # African market context (if present in the profile)
    african_ctx = bm.get('african_context', {})
    if african_ctx:
        lines += ["", "AFRICAN MARKET CONTEXT (incorporate into findings):"]
        for k, v in african_ctx.items():
            label = k.replace('_', ' ').title()
            lines.append("  * {}: {}".format(label, v))

    if rev_context:
        lines += ["", rev_context]

    lines += [
        "",
        "MANDATORY RULE: Every finding you write MUST compare a specific figure from the",
        "client's data against the benchmark above. State the gap in absolute terms",
        "(e.g. 'client gross margin is 21.3% vs industry median 33.2% -- a 11.9pp gap').",
        "Never make a finding without citing a specific number from the uploaded data.",
    ]

    return '\n'.join(lines)


def calculate_gap(client_value: float, benchmark_value: float,
                  metric_name: str, higher_is_better: bool = True,
                  currency: str = '', annual_revenue: float = 0) -> dict:
    """
    Calculate the gap between client and benchmark.
    Returns a dict with gap analysis for use in agent responses.
    """
    gap = client_value - benchmark_value
    # For ratio metrics (< 2), express as percentage points
    gap_pp = gap * 100 if benchmark_value < 2 else gap

    status = 'on_par'
    if higher_is_better:
        if gap < -0.05:
            status = 'critical'
        elif gap < -0.02:
            status = 'warning'
        elif gap > 0.05:
            status = 'above_benchmark'
    else:
        if gap > 0.05:
            status = 'critical'
        elif gap > 0.02:
            status = 'warning'
        elif gap < -0.05:
            status = 'above_benchmark'

    result = {
        'metric': metric_name,
        'client_value': client_value,
        'benchmark_value': benchmark_value,
        'gap': gap,
        'gap_pp': gap_pp,
        'status': status,
    }

    if annual_revenue > 0 and benchmark_value < 2:
        financial_impact = abs(gap) * annual_revenue
        result['annual_financial_impact'] = financial_impact
        result['impact_formatted'] = (
            "{} {:,.0f}".format(currency, financial_impact) if currency
            else "{:,.0f}".format(financial_impact)
        )

    return result
