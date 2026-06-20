"""
Action Simulator — deterministic prescriptive engine.

Takes the analytics Imara already produced (financial_figures, ratios, Imara Score
components) and projects the OUTCOME of taking recommended actions. All maths is
deterministic and traceable — the LLM is never in the numbers. Outputs are clearly
indicative estimates.

Design (driver-based scenario model, FP&A best practice):
  derive_actions(report)  -> candidate actions grounded in the firm's ratios vs sector
  apply_actions(report, selected, scenario) -> projected figures, ratios, fundamentals
                                               score and an estimated Imara Score, plus
                                               cash released and per-action contributions.
"""
from services.financial_ratios import compute_ratios, fundamentals_score

# Actions rarely land at 100%. Realisation haircut by named scenario (base/best/worst).
SCENARIOS = {"optimistic": 1.0, "expected": 0.6, "pessimistic": 0.3}
# A 1% price rise softens volume by ~0.5% (simple constant elasticity for the MVP).
PRICE_VOLUME_ELASTICITY = -0.5


def _num(d, k, default=0.0):
    v = (d or {}).get(k)
    return float(v) if isinstance(v, (int, float)) else default


def _baseline_figs(report: dict) -> dict:
    """Normalise the stored figures into a complete set the model can work with."""
    figs = dict(report.get("financial_figures") or {})
    rev = _num(figs, "revenue") or float(report.get("annual_revenue") or 0)
    figs["revenue"] = rev
    if "gross_profit" not in figs and "cogs" in figs:
        figs["gross_profit"] = rev - _num(figs, "cogs")
    if "cogs" not in figs and "gross_profit" in figs:
        figs["cogs"] = rev - _num(figs, "gross_profit")
    gp = _num(figs, "gross_profit")
    # opex implied by gross - operating (the lever we trim)
    figs["opex"] = max(0.0, gp - _num(figs, "operating_profit"))
    return figs


def derive_actions(report: dict) -> list:
    """Candidate actions from the firm's own ratios vs their sector benchmark.
    Each action is grounded in real numbers (the gap IS the maximum magnitude)."""
    ratios = report.get("financial_ratios") or {}
    figs = _baseline_figs(report)
    rev = _num(figs, "revenue")
    opex = _num(figs, "opex")
    cur = report.get("currency") or "ZAR"

    def rv(key, sub="value"):
        return (ratios.get(key) or {}).get(sub)

    out = []
    gm, gmb = rv("gross_margin"), rv("gross_margin", "benchmark")
    if gm is not None and gmb is not None and gmb - gm > 0.5:
        out.append({"id": "gross_margin", "driver": "gross_margin_pp",
                    "label": "Lift gross margin toward sector benchmark",
                    "max": round(gmb - gm, 1), "unit": "pp",
                    "rationale": "Gross margin {:.1f}% vs sector {:.1f}% — closing the gap adds margin on every sale.".format(gm, gmb)})
    om, omb = rv("operating_margin"), rv("operating_margin", "benchmark")
    if om is not None and omb is not None and omb - om > 0.5 and opex > 0 and rev > 0:
        needed_pct = ((omb - om) / 100.0 * rev) / opex * 100.0
        out.append({"id": "opex", "driver": "opex_reduction_pct",
                    "label": "Trim overheads toward sector operating margin",
                    "max": round(min(needed_pct, 25.0), 1), "unit": "%",
                    "rationale": "Operating margin {:.1f}% vs sector {:.1f}% — disciplined overhead control closes the gap.".format(om, omb)})
    dd, ddb = rv("debtor_days"), rv("debtor_days", "benchmark")
    if dd is not None and ddb is not None and dd - ddb > 5:
        out.append({"id": "debtor_days", "driver": "debtor_days_reduction",
                    "label": "Collect receivables faster",
                    "max": round(dd - ddb), "unit": "days",
                    "rationale": "Debtor days {:.0f} vs sector {:.0f} — faster collection frees up cash.".format(dd, ddb)})
    idd, idb = rv("inventory_days"), rv("inventory_days", "benchmark")
    if idd is not None and idb is not None and idd - idb > 5:
        out.append({"id": "inventory_days", "driver": "inventory_days_reduction",
                    "label": "Reduce slow-moving stock",
                    "max": round(idd - idb), "unit": "days",
                    "rationale": "Inventory days {:.0f} vs sector {:.0f} — leaner stock frees up cash.".format(idd, idb)})
    # Always-available upside levers (explore growth even with no gap)
    out.append({"id": "revenue_growth", "driver": "revenue_growth_pct",
                "label": "Grow revenue (win more volume)", "max": 25.0, "unit": "%", "default": 10.0,
                "rationale": "Model winning more business at current margins."})
    out.append({"id": "price", "driver": "price_increase_pct",
                "label": "Raise prices", "max": 15.0, "unit": "%", "default": 5.0,
                "rationale": "Price rises lift margin but soften volume (elasticity modelled)."})
    for a in out:
        a.setdefault("default", a["max"])
        a["currency"] = cur
    return out


def _project(figs: dict, drivers: dict, capture: float):
    """Apply driver deltas (already capture-scaled outside via `capture`) to the figures."""
    rev = _num(figs, "revenue"); cogs = _num(figs, "cogs"); opex = _num(figs, "opex")
    receivables = _num(figs, "receivables"); inventory = _num(figs, "inventory")
    current_assets = _num(figs, "current_assets"); current_liabilities = _num(figs, "current_liabilities")
    payables = _num(figs, "payables"); total_debt = _num(figs, "total_debt")
    equity = _num(figs, "equity"); interest = _num(figs, "interest")

    growth = capture * _num(drivers, "revenue_growth_pct") / 100.0
    price = capture * _num(drivers, "price_increase_pct") / 100.0
    vol_mult = (1 + growth) * (1 + PRICE_VOLUME_ELASTICITY * price)
    rev_new = rev * vol_mult * (1 + price)
    cogs_new = cogs * vol_mult  # COGS scales with volume, not price
    gm_pp = capture * _num(drivers, "gross_margin_pp")
    if gm_pp and rev_new > 0:
        cogs_new = max(0.0, cogs_new - rev_new * (gm_pp / 100.0))
    opex_new = opex * (1 - capture * _num(drivers, "opex_reduction_pct") / 100.0)
    gross_new = rev_new - cogs_new
    operating_new = gross_new - opex_new
    net_new = operating_new - interest

    cash_released = 0.0
    receivables_new, inventory_new = receivables, inventory
    if rev > 0:
        rel = (capture * _num(drivers, "debtor_days_reduction") / 365.0) * rev
        cash_released += rel
        receivables_new = max(0.0, receivables - rel)
    if cogs > 0:
        rel = (capture * _num(drivers, "inventory_days_reduction") / 365.0) * cogs
        cash_released += rel
        inventory_new = max(0.0, inventory - rel)

    new_figs = {
        "revenue": rev_new, "cogs": cogs_new, "gross_profit": gross_new,
        "operating_profit": operating_new, "net_profit": net_new,
        "receivables": receivables_new, "inventory": inventory_new,
        "current_assets": current_assets, "current_liabilities": current_liabilities,
        "payables": payables, "total_debt": total_debt, "equity": equity, "interest": interest,
    }
    return new_figs, cash_released


def _estimate_imara(report: dict, new_fund: float):
    """Project the Imara Score by moving Profitability's fundamentals-anchored portion
    (0.6 weight) and holding the LLM-driven components constant, then re-normalising."""
    comps = report.get("imara_components") or []
    old_fund = float(report.get("financial_fundamentals_score") or 0)
    if not comps:
        return report.get("imara_score")
    total_w = 0.0; acc = 0.0
    for c in comps:
        w = float(c.get("weight") or 0); v = float(c.get("value") or 0)
        if c.get("label") == "Profitability" and old_fund:
            v = max(0.0, min(100.0, v + 0.6 * (new_fund - old_fund)))
        total_w += w; acc += v * w
    return int(round(acc / total_w)) if total_w else report.get("imara_score")


def apply_actions(report: dict, selected: list, scenario: str = "expected") -> dict:
    capture = SCENARIOS.get(scenario, 0.6)
    figs = _baseline_figs(report)
    industry = report.get("industry_key") or "general"
    rev = _num(figs, "revenue")
    catalog = {a["id"]: a for a in derive_actions(report)}

    drivers = {}; applied = []
    for sel in (selected or []):
        a = catalog.get(sel.get("id"))
        if not a:
            continue
        try:
            intensity = max(0.0, min(1.0, float(sel.get("intensity", 1.0))))
        except (TypeError, ValueError):
            intensity = 1.0
        mag = float(a.get("default", a.get("max", 0))) * intensity
        drivers[a["driver"]] = drivers.get(a["driver"], 0.0) + mag
        applied.append({"id": a["id"], "label": a["label"], "driver": a["driver"],
                        "applied": round(mag, 2), "unit": a.get("unit")})

    base_figs, _ = _project(figs, {}, 1.0)
    base_ratios = compute_ratios(base_figs, industry, rev)
    base_fund = float(report.get("financial_fundamentals_score")
                      or (fundamentals_score(base_ratios, industry).get("score") or 0))
    proj_figs, cash_released = _project(figs, drivers, capture)
    proj_ratios = compute_ratios(proj_figs, industry, rev)
    proj_fund = fundamentals_score(proj_ratios, industry).get("score") or 0

    def snap(f, ratios):
        def rv(k):
            return (ratios.get(k) or {}).get("value")
        return {
            "revenue": round(_num(f, "revenue")),
            "gross_profit": round(_num(f, "gross_profit")),
            "operating_profit": round(_num(f, "operating_profit")),
            "net_profit": round(_num(f, "net_profit")),
            "gross_margin": rv("gross_margin"), "operating_margin": rv("operating_margin"),
            "net_margin": rv("net_margin"), "current_ratio": rv("current_ratio"),
            "debtor_days": rv("debtor_days"), "interest_coverage": rv("interest_coverage"),
        }

    # Imara Score: apply the MODELLED delta to the canonical baseline so "no actions"
    # yields exactly zero change (re-normalisation rounding can't leak a phantom delta).
    model_base = _estimate_imara(report, base_fund) or 0
    model_proj = _estimate_imara(report, proj_fund) or 0
    score_delta = model_proj - model_base
    canonical = report.get("imara_score")
    base_score = canonical if canonical is not None else model_base
    baseline = snap(base_figs, base_ratios)
    baseline["fundamentals_score"] = int(round(base_fund))
    baseline["imara_score"] = base_score
    projected = snap(proj_figs, proj_ratios)
    projected["fundamentals_score"] = int(round(proj_fund))
    projected["imara_score"] = int(max(0, min(100, round(base_score + score_delta))))

    return {
        "scenario": scenario, "capture_factor": capture,
        "currency": report.get("currency") or "ZAR",
        "baseline": baseline, "projected": projected,
        "cash_released": round(cash_released),
        "applied_actions": applied,
        "net_profit_delta": projected["net_profit"] - baseline["net_profit"],
        "imara_score_delta": projected["imara_score"] - (baseline["imara_score"] or 0),
        "disclaimer": ("Indicative model: deterministic projection from your figures under a {} "
                       "scenario (actions realised at {:.0f}%). Not a guarantee.".format(scenario, capture * 100)),
    }
