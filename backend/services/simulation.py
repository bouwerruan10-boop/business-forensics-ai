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
# SA company income tax — applied to incremental operating profit so 'net' is realistic.
TAX_RATE = 0.27


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
    # Supplier benchmarking: a grounded opex-reduction lever from the supplier-savings engine.
    sb = report.get("supplier_benchmark") or {}
    if sb.get("available") and opex > 0:
        _shi = float(sb.get("total_est_saving_high") or 0)
        _slo = float(sb.get("total_est_saving_low") or 0)
        if _shi > 0:
            _mid = (_slo + _shi) / 2.0
            out.append({"id": "supplier_switch", "driver": "opex_reduction_pct",
                        "label": "Switch to benchmarked lower-cost suppliers",
                        "max": round(min(100.0, _shi / opex * 100.0), 1), "unit": "%",
                        "default": round(min(100.0, _mid / opex * 100.0), 1),
                        "rationale": "Benchmarking flags about R{:,.0f}-R{:,.0f}/yr of supplier savings at equivalent service (bank charges, card fees, telecoms, insurance, software).".format(_slo, _shi)})
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
    # Plausibility guards (verification sanity bounds): no negative/absurd states.
    rev_new = max(0.0, rev_new)
    if rev_new > 0:
        cogs_new = min(max(cogs_new, 0.02 * rev_new), 0.98 * rev_new)
    else:
        cogs_new = max(0.0, cogs_new)
    opex_new = max(0.0, opex_new)
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
    proj_figs, cash_released = _project(figs, drivers, capture)
    # Tax realism + baseline consistency: baseline net = the report's actual net;
    # projected net = actual net + the AFTER-TAX incremental operating profit.
    actual_net = _num(figs, "net_profit") or _num(base_figs, "net_profit")
    delta_op = _num(proj_figs, "operating_profit") - _num(base_figs, "operating_profit")
    base_figs["net_profit"] = actual_net
    proj_figs["net_profit"] = actual_net + (delta_op * (1 - TAX_RATE) if delta_op > 0 else delta_op)
    base_ratios = compute_ratios(base_figs, industry, rev)
    proj_ratios = compute_ratios(proj_figs, industry, rev)
    base_fund = float(report.get("financial_fundamentals_score")
                      or (fundamentals_score(base_ratios, industry).get("score") or 0))
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


# ── v2: sensitivity ranking (tornado) + Monte Carlo uncertainty ────────────
_BAND_THRESHOLDS = (35, 50, 65, 80)  # E<35, D, C, B, A>=80


def _next_band_threshold(score):
    for t in _BAND_THRESHOLDS:
        if score < t:
            return t
    return None


def rank_levers(report: dict, scenario: str = "expected") -> list:
    """Tornado/sensitivity: each action's STANDALONE impact, ranked — the biggest levers."""
    out = []
    for a in derive_actions(report):
        r = apply_actions(report, [{"id": a["id"], "intensity": 1.0}], scenario)
        out.append({"id": a["id"], "label": a["label"], "unit": a.get("unit"),
                    "score_impact": r["imara_score_delta"],
                    "profit_impact": r["net_profit_delta"],
                    "cash_released": r["cash_released"]})
    out.sort(key=lambda x: (x["score_impact"], x["profit_impact"]), reverse=True)
    return out


def monte_carlo(report: dict, selected: list, n: int = 1000, seed: int = 42) -> dict:
    """Probabilistic outcome: sample how fully each action lands (triangular 0.2/0.6/1.05)
    plus market noise on revenue, over n seeded runs. Returns p10/p50/p90 of the net-profit
    delta and the projected Imara Score, and the probability of reaching the next band."""
    import random
    import statistics
    rng = random.Random(seed)
    figs = _baseline_figs(report)
    industry = report.get("industry_key") or "general"
    rev = _num(figs, "revenue")
    catalog = {a["id"]: a for a in derive_actions(report)}
    sel = [s for s in (selected or []) if catalog.get(s.get("id"))]

    base_figs, _ = _project(figs, {}, 1.0)
    base_operating = _num(base_figs, "operating_profit")
    actual_net = _num(figs, "net_profit") or _num(base_figs, "net_profit")
    base_fund = float(report.get("financial_fundamentals_score")
                      or (fundamentals_score(compute_ratios(base_figs, industry, rev), industry).get("score") or 0))
    canonical = report.get("imara_score")
    model_base = _estimate_imara(report, base_fund) or 0
    base_score = canonical if canonical is not None else model_base

    net_deltas = []
    scores = []
    for _ in range(max(1, n)):
        drivers = {}
        for s in sel:
            a = catalog[s["id"]]
            try:
                intensity = max(0.0, min(1.0, float(s.get("intensity", 1.0))))
            except (TypeError, ValueError):
                intensity = 1.0
            cap = rng.triangular(0.2, 1.05, 0.6)  # how fully this action lands
            drivers[a["driver"]] = drivers.get(a["driver"], 0.0) + float(a.get("default", a.get("max", 0))) * intensity * cap
        drivers["revenue_growth_pct"] = drivers.get("revenue_growth_pct", 0.0) + rng.gauss(0.0, 4.0)  # market noise (pp)
        pf, _ = _project(figs, drivers, 1.0)
        delta_op = _num(pf, "operating_profit") - base_operating
        net_deltas.append((delta_op * (1 - TAX_RATE) if delta_op > 0 else delta_op))
        fund = fundamentals_score(compute_ratios(pf, industry, rev), industry).get("score") or 0
        sc = base_score + ((_estimate_imara(report, fund) or 0) - model_base)
        scores.append(max(0.0, min(100.0, sc)))

    def pcts(xs):
        xs = sorted(xs)
        if len(xs) >= 2:
            q = statistics.quantiles(xs, n=10)
            return {"p10": round(q[0]), "p50": round(statistics.median(xs)), "p90": round(q[8])}
        return {"p10": round(xs[0]), "p50": round(xs[0]), "p90": round(xs[0])}

    nb = _next_band_threshold(round(base_score))
    prob = (sum(1 for sc in scores if nb is not None and sc >= nb) / len(scores)) if scores else 0.0
    return {
        "iterations": n, "seed": seed, "currency": report.get("currency") or "ZAR",
        "base_score": round(base_score), "next_band_threshold": nb,
        "prob_reach_next_band": round(prob, 3),
        "net_profit_delta": pcts(net_deltas), "imara_score": pcts(scores),
        "disclaimer": ("Probabilistic estimate over {} simulations sampling how fully each action "
                       "lands plus market noise. Indicative, not a guarantee.".format(n)),
    }


# ── v3: bundle optimiser ───────────────────────────────────────────────────
# "Which combination of actions should I pursue first?" An SME has limited
# capacity, so the real question is the BEST SUBSET of actions under an action-
# count budget. Because actions interact (gross-margin + growth compound through
# _project), greedy ranking can be wrong — so we evaluate every bundle jointly
# via apply_actions. With <=6 candidate actions this exhaustive search is optimal
# and cheap, and it stays fully deterministic (no LLM, no sampling).
from itertools import combinations as _combinations


def optimize_actions(report: dict, scenario: str = "expected",
                     max_actions: int = 3, objective: str = "imara") -> dict:
    actions = derive_actions(report)
    ids = [a["id"] for a in actions]
    labels = {a["id"]: a["label"] for a in actions}
    try:
        max_actions = max(1, min(int(max_actions), len(ids)))
    except (TypeError, ValueError):
        max_actions = min(3, len(ids))

    def metric(res):
        if objective == "profit":
            return res["net_profit_delta"]
        if objective == "cash":
            return res["cash_released"]
        return res["imara_score_delta"]

    evaluated, best_by_size = [], {}
    for k in range(1, max_actions + 1):
        for combo in _combinations(ids, k):
            sel = [{"id": i, "intensity": 1.0} for i in combo]
            res = apply_actions(report, sel, scenario)
            rec = {
                "ids": list(combo), "labels": [labels[i] for i in combo], "size": k,
                "objective_value": metric(res),
                "imara_score_delta": res["imara_score_delta"],
                "net_profit_delta": res["net_profit_delta"],
                "cash_released": res["cash_released"],
            }
            evaluated.append(rec)
            if k not in best_by_size or rec["objective_value"] > best_by_size[k]["objective_value"]:
                best_by_size[k] = rec

    # Best value first; on ties prefer the SMALLER bundle (less effort for same lift).
    evaluated.sort(key=lambda r: (-r["objective_value"], r["size"]))
    best = evaluated[0] if evaluated else None
    curve = [best_by_size[k] for k in sorted(best_by_size)]
    return {
        "scenario": scenario, "objective": objective, "max_actions": max_actions,
        "currency": report.get("currency") or "ZAR",
        "best_bundle": best,
        "top_bundles": evaluated[:5],
        "marginal_curve": [
            {"size": c["size"], "objective_value": c["objective_value"], "labels": c["labels"]}
            for c in curve
        ],
        "disclaimer": ("Exhaustive deterministic search over action bundles under a {}-action budget "
                       "({} scenario). Indicative model projections, not guarantees.".format(max_actions, scenario)),
    }


# ── v4: macro stress test (economics agent ↔ simulator) ────────────────────
# Projects the firm under probability-weighted macro scenarios (IFRS-9 style:
# base/adverse/upside), transmitting each macro shock through the firm's OWN
# structure (floating debt, energy-intensive opex, FX-exposed costs, demand
# cyclicality). Deterministic; reuses compute_ratios / fundamentals_score /
# _estimate_imara. A single scenario understates risk under non-linearity, so we
# weight three. The result is an OVERLAY (resilience view), not a Score rewrite.
from services.macro_data import SECTOR_PROFILE, FLOATING_DEBT_SHARE, ENERGY_OPEX_FACTOR, SA_MACRO

MACRO_SCENARIOS = [
    ("Base",    0.50, dict(repo_bps=0,    inflation_pp=0,  tariff_pct=12.7, zar_pct=0,   demand_pct=1)),
    ("Adverse", 0.25, dict(repo_bps=200,  inflation_pp=3,  tariff_pct=18.0, zar_pct=-12, demand_pct=-3)),
    ("Upside",  0.25, dict(repo_bps=-100, inflation_pp=-1, tariff_pct=8.0,  zar_pct=8,   demand_pct=3)),
]
_INFLATION_PASSTHROUGH = 0.5   # firms pass ~half of cost inflation to prices


def macro_stress_test(report: dict) -> dict:
    figs = _baseline_figs(report)
    industry = report.get("industry_key") or "general"
    prof = SECTOR_PROFILE.get(industry, SECTOR_PROFILE["general"])
    rev = _num(figs, "revenue"); cogs = _num(figs, "cogs"); opex = _num(figs, "opex")
    op = _num(figs, "operating_profit"); interest = _num(figs, "interest")
    debt = _num(figs, "total_debt")
    actual_net = _num(figs, "net_profit") or (op - interest)
    floating = debt * FLOATING_DEBT_SHARE
    energy_opex = opex * ENERGY_OPEX_FACTOR * prof["energy"] / 0.5
    fx_cost = (cogs + opex) * prof["fx"] * 0.4

    base_score = report.get("imara_score")
    results = []
    for name, weight, sc in MACRO_SCENARIOS:
        d_interest = floating * (sc["repo_bps"] / 10000.0)
        d_energy = energy_opex * (sc["tariff_pct"] / 100.0)
        d_inflation = (cogs + opex) * (sc["inflation_pp"] / 100.0) * (1 - _INFLATION_PASSTHROUGH)
        d_fx = fx_cost * (-sc["zar_pct"] / 100.0)                 # weaker rand (neg) raises cost
        demand = (sc["demand_pct"] / 100.0) * prof["demand"]

        rev_new = max(0.0, rev * (1 + demand))
        cogs_new = cogs * (1 + demand)
        opex_new = max(0.0, opex + d_energy + d_inflation + d_fx)
        gross_new = rev_new - cogs_new
        op_new = gross_new - opex_new
        pre_tax_delta = (op_new - op) - d_interest
        net_new = actual_net + (pre_tax_delta * (1 - TAX_RATE) if pre_tax_delta > 0 else pre_tax_delta)

        proj_figs = {"revenue": rev_new, "cogs": cogs_new, "gross_profit": gross_new,
                     "operating_profit": op_new, "net_profit": net_new,
                     "receivables": _num(figs, "receivables"), "inventory": _num(figs, "inventory"),
                     "current_assets": _num(figs, "current_assets"), "current_liabilities": _num(figs, "current_liabilities"),
                     "total_debt": debt, "equity": _num(figs, "equity"), "interest": interest + d_interest}
        proj_ratios = compute_ratios(proj_figs, industry, rev)
        proj_fund = fundamentals_score(proj_ratios, industry).get("score") or 0
        model_proj = _estimate_imara(report, proj_fund)
        model_base = _estimate_imara(report, report.get("financial_fundamentals_score") or proj_fund)
        score = None
        if base_score is not None and model_proj is not None and model_base is not None:
            score = int(max(0, min(100, round(base_score + (model_proj - model_base)))))
        results.append({"scenario": name, "weight": weight,
                        "net_profit": round(net_new), "operating_profit": round(op_new),
                        "imara_score": score})

    exp_net = round(sum(r["weight"] * r["net_profit"] for r in results))
    sc_by = {r["scenario"]: r for r in results}
    adverse = sc_by["Adverse"]; base = sc_by["Base"]
    score_drop = (base["imara_score"] - adverse["imara_score"]) if (base["imara_score"] is not None and adverse["imara_score"] is not None) else None
    # Resilience reflects the ADVERSE profit outcome (the honest fragility signal),
    # not just the sticky multi-factor Score: flipping to a loss is the strongest signal.
    base_net = actual_net; adv_net = adverse["net_profit"]
    res = 100 - min(50, max(0, score_drop or 0) * 5)
    flips_to_loss = base_net > 0 and adv_net <= 0
    if flips_to_loss:
        res = min(res, 35)                                   # profitable today, loss under adverse
    elif base_net > 0 and adv_net < 0.5 * base_net:
        res = min(res, 60)                                   # >50% profit erosion
    resilience = int(max(0, min(100, res)))
    resilience_label = ("fragile" if resilience < 50 else "moderate" if resilience < 75 else "robust")
    return {
        "as_of": SA_MACRO["as_of"], "industry": industry,
        "baseline": {"net_profit": round(actual_net), "imara_score": base_score},
        "scenarios": results,
        "expected_net_profit": exp_net,
        "adverse_score_drop": score_drop,
        "macro_resilience": resilience,
        "macro_resilience_label": resilience_label,
        "flips_to_loss_under_adverse": flips_to_loss,
        "disclaimer": ("Probability-weighted macro stress (base 50% / adverse 25% / upside 25%), each shock "
                       "transmitted through the firm's own cost, debt and demand structure. Indicative overlay, "
                       "not a change to the headline Imara Score, and not a credit decision."),
    }
