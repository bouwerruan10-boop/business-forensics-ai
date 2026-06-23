"""
SA macro-economic snapshot + deterministic firm macro-sensitivity engine.

The EconomicsAgent and the macro stress test read the macro environment and
translate it into effects on ONE firm's "internal economy" — using the firm's
OWN statements (bottom-up sensitivity), not LLM guesswork. Same anti-hallucination
DNA as the financial-ratio engine: numbers are deterministic; the LLM only narrates.

The snapshot is a curated, DATED set of indicators (the legislation-corpus pattern).
A live refresh from the World Bank API (no key) / SARB is a later phase; for now the
dated snapshot keeps the pipeline self-contained and reproducible.
"""

# Curated dated snapshot — refresh periodically. Each value carries provenance via as_of/source.
from services import sa_rates as _sa_rates   # single source of truth for repo/prime (avoids cross-agent drift)
SA_MACRO = {
    "as_of": "2026-06",
    "source": "Curated from SARB / Stats SA / World Bank (snapshot; not live)",
    "indicators": {
        "repo_rate":        {"value": _sa_rates.REPO_RATE, "unit": "%", "label": "SARB repo rate"},
        "prime_rate":       {"value": _sa_rates.PRIME_RATE, "unit": "%", "label": "Prime lending rate"},
        "cpi_inflation":    {"value": 3.5, "unit": "%", "label": "CPI inflation (SARB target 3-6%)"},
        "gdp_growth":       {"value": 1.3, "unit": "%", "label": "Real GDP growth (~1.4% next year est.)"},
        "zar_usd":          {"value": 18.2, "unit": "ZAR/USD", "label": "Rand / US dollar"},
        "electricity_tariff": {"value": 12.7, "unit": "%/yr", "label": "Eskom/NERSA tariff increase (~+24% over 3y)"},
        "unemployment":     {"value": 32.9, "unit": "%", "label": "Unemployment rate"},
    },
    "regime": "Disinflation + an easing-bias rate cycle; electricity tariffs run well above CPI; "
              "load-shedding has eased sharply but tariff and input-cost pressure persist.",
}

# Per-sector macro intensity (0-1) — which macro drivers bite hardest, from SA sector research.
# energy: electricity exposure | fx: import/export & input exposure | rate: debt/rate sensitivity | demand: cyclicality
SECTOR_PROFILE = {
    "manufacturing":        {"energy": 0.90, "fx": 0.70, "rate": 0.60, "demand": 0.60},
    "agriculture":          {"energy": 0.50, "fx": 0.70, "rate": 0.90, "demand": 0.50},
    "construction":         {"energy": 0.40, "fx": 0.45, "rate": 0.90, "demand": 0.75},
    "retail":               {"energy": 0.50, "fx": 0.55, "rate": 0.60, "demand": 0.85},
    "logistics":            {"energy": 0.65, "fx": 0.70, "rate": 0.60, "demand": 0.60},
    "hospitality":          {"energy": 0.60, "fx": 0.35, "rate": 0.55, "demand": 0.90},
    "professional_services":{"energy": 0.20, "fx": 0.30, "rate": 0.40, "demand": 0.55},
    "technology":           {"energy": 0.30, "fx": 0.55, "rate": 0.40, "demand": 0.55},
    "general":              {"energy": 0.50, "fx": 0.50, "rate": 0.60, "demand": 0.60},
}

# Modelling assumptions (transparent + documented, not hidden in the LLM).
FLOATING_DEBT_SHARE = 0.75   # SA SME bank debt is largely prime-linked / variable rate
ENERGY_OPEX_FACTOR = 0.18    # baseline share of opex that is electricity/energy (scaled by sector energy intensity)
TAX_RATE = 0.27


def _num(d, k, default=0.0):
    v = (d if isinstance(d, dict) else {}).get(k)
    if isinstance(v, (int, float)):
        import math as _m
        f = float(v)
        return f if _m.isfinite(f) else default
    return default


def _level(impact_abs, operating_profit, revenue):
    """Classify an annual ZAR impact into low/medium/high exposure."""
    base = abs(operating_profit) if operating_profit else max(revenue * 0.05, 1.0)
    r = impact_abs / base if base else 0.0
    return "high" if r >= 0.25 else "medium" if r >= 0.10 else "low"


def firm_macro_sensitivity(report: dict) -> dict:
    """Bottom-up: derive the firm's exposure to rates/inflation/energy/FX from its OWN figures."""
    figs = dict(report.get("financial_figures") or {})
    industry = (report.get("industry_key") or "general")
    prof = SECTOR_PROFILE.get(industry, SECTOR_PROFILE["general"])
    rev = _num(figs, "revenue") or float(report.get("annual_revenue") or 0)
    gp = _num(figs, "gross_profit")
    op = _num(figs, "operating_profit")
    opex = max(0.0, gp - op) if (gp or op) else _num(figs, "opex")
    cogs = _num(figs, "cogs") or max(0.0, rev - gp)
    debt = _num(figs, "total_debt")
    _num(figs, "interest")

    # Interest rate: +100bps on the floating share of debt -> extra annual interest.
    floating = debt * FLOATING_DEBT_SHARE
    d_interest_100 = floating * 0.01
    rate = {"driver": "Interest rates", "per_100bps_zar": round(d_interest_100),
            "floating_debt_zar": round(floating),
            "exposure": _level(d_interest_100, op, rev),
            "note": "≈R{:,.0f} extra annual interest per +100bps on ~{:.0f}% floating debt.".format(d_interest_100, FLOATING_DEBT_SHARE*100)}

    # Inflation: +1pp cost inflation on the cost base not offset by pricing power.
    cost_base = cogs + opex
    d_cost_1pp = cost_base * 0.01
    inflation = {"driver": "Inflation / input costs", "per_1pp_zar": round(d_cost_1pp),
                 "exposure": _level(d_cost_1pp, op, rev),
                 "note": "≈R{:,.0f} added cost per +1pp input inflation if not passed through.".format(d_cost_1pp)}

    # Energy: electricity tariff increase on the (sector-scaled) energy portion of opex.
    tariff = SA_MACRO["indicators"]["electricity_tariff"]["value"]
    energy_opex = opex * ENERGY_OPEX_FACTOR * prof["energy"] / 0.5  # normalise sector intensity around the general 0.5
    d_energy = energy_opex * (tariff / 100.0)
    energy = {"driver": "Electricity tariffs", "annual_zar": round(d_energy),
              "exposure": _level(d_energy, op, rev),
              "note": "≈R{:,.0f}/yr from the {:.1f}% tariff path on an energy-intensive ({}) cost base.".format(d_energy, tariff, industry)}

    # FX: sector-driven; a 10% rand move on the import/export-exposed slice of the cost base.
    fx_exposed = cost_base * prof["fx"] * 0.4  # conservative slice
    d_fx_10 = fx_exposed * 0.10
    fx = {"driver": "Rand / FX", "per_10pct_zar": round(d_fx_10),
          "exposure": _level(d_fx_10, op, rev),
          "note": "≈R{:,.0f} cost swing per 10% rand move on FX-exposed inputs (sector estimate).".format(d_fx_10)}

    drivers = [rate, inflation, energy, fx]
    order = {"high": 0, "medium": 1, "low": 2}
    top = sorted(drivers, key=lambda d: order[d["exposure"]])[0]
    overall = "high" if any(d["exposure"] == "high" for d in drivers) else \
              "medium" if any(d["exposure"] == "medium" for d in drivers) else "low"
    return {"industry": industry, "as_of": SA_MACRO["as_of"], "drivers": drivers,
            "top_driver": top["driver"], "overall_exposure": overall}


def macro_summary_text(report: dict) -> str:
    """Compact grounded string for the EconomicsAgent prompt + the report."""
    ind = SA_MACRO["indicators"]
    s = firm_macro_sensitivity(report)
    head = ("SA MACRO SNAPSHOT (as of {}; cite these, do not invent figures): repo {}%, prime {}%, CPI {}%, "
            "GDP growth {}%, ZAR/USD {}, electricity tariff +{}%/yr, unemployment {}%. {}").format(
        SA_MACRO["as_of"], ind["repo_rate"]["value"], ind["prime_rate"]["value"], ind["cpi_inflation"]["value"],
        ind["gdp_growth"]["value"], ind["zar_usd"]["value"], ind["electricity_tariff"]["value"],
        ind["unemployment"]["value"], SA_MACRO["regime"])
    expo = " | ".join("{}: {} ({})".format(d["driver"], d["exposure"], d["note"]) for d in s["drivers"])
    return head + "\nFIRM MACRO EXPOSURE (computed from the firm's own statements): overall {}; top driver {}. {}".format(
        s["overall_exposure"], s["top_driver"], expo)
