"""
Supplier benchmarking engine — turns extracted expense line items into spend-vs-
benchmark assessments (Layer A) and lower-cost-supplier opportunities (Layer B).

All deterministic. Savings are indicative RANGES off the firm's actual spend at
EQUIVALENT service, each dated + sourced. Never invents a competitor's exact price;
never feeds the Imara Score (decision-support / opportunity only). Feeds the Action
Simulator's opex lever so the user can see the projected Score uplift if they act.
"""

import re
from services.expense_lines import extract_expense_lines
from services.supplier_catalog import category_reference


def run_supplier_benchmark(financial_text: str, revenue, profile=None) -> dict:
    profile = profile or {}
    lines = extract_expense_lines(financial_text or "")
    if not lines:
        return {"available": False,
                "reason": "No itemised expense lines found — the financials gave only totals. "
                          "Upload an itemised income statement / management accounts to benchmark suppliers."}

    revenue = float(revenue or 0)
    banking_partner = (profile.get("banking_partner") or "")
    opportunities = []
    total_low = total_high = 0.0

    for line in lines:
        cat = line["category"]
        spend = float(line["amount"])
        ref = category_reference(cat)
        pct = (spend / revenue * 100) if revenue else None

        # ── Layer A: magnitude vs benchmark band ──
        band = ref.get("benchmark_pct")
        status, over_amount = "no_benchmark", None
        if band and pct is not None:
            lo, hi = band
            if pct > hi:
                status, over_amount = "above", round((pct - hi) / 100 * revenue, 2)
            elif pct < lo:
                status = "below"
            else:
                status = "within"

        # ── Layer B: lower-cost supplier substitution ──
        providers = ref.get("low_cost_providers") or []
        sav = ref.get("typical_savings_pct")
        raw_low = (line.get("raw") or "").lower()

        def _match(names, hay):
            for n in (names or []):
                if re.search(r"\b" + re.escape(n.lower()) + r"\b", hay):
                    return n
            return None

        # Incumbent: the banking partner from the profile, else a higher-cost provider
        # named in the expense line itself (e.g. "Telephone Vodacom contract").
        detected = _match(ref.get("higher_cost_incumbents"), raw_low)
        if cat == "bank_charges" and banking_partner:
            incumbent = banking_partner
            incumbent_higher = any(h in banking_partner.lower() for h in ref.get("higher_cost_incumbents", []))
        else:
            incumbent = detected
            incumbent_higher = detected is not None
        already_low = _match(ref.get("low_cost_providers"), raw_low) is not None   # already on a cheap provider

        save_low = save_high = None
        confidence = "low"
        if line.get("substitutable") and providers and sav and not already_low:
            sl, sh = sav
            if incumbent_higher:
                save_low, save_high, confidence = round(sl * spend, 2), round(sh * spend, 2), "medium"
            elif status == "above":
                a, b = over_amount, round(sh * spend, 2)
                save_low, save_high, confidence = round(min(a, b), 2), round(max(a, b), 2), "medium"
            # else: options exist but no hard saving claimed (informational)

        if save_low is not None:
            total_low += save_low
            total_high += save_high

        opportunities.append({
            "category": cat, "label": line["label"], "spend": spend,
            "pct_of_revenue": round(pct, 2) if pct is not None else None,
            "benchmark_pct": band, "status": status, "over_benchmark": over_amount,
            "equivalence": ref.get("equivalence"),
            "alternatives": providers, "incumbent": incumbent,
            "est_saving_low": save_low, "est_saving_high": save_high,
            "confidence": confidence,
            "as_of": ref.get("as_of"), "source": ref.get("source"),
        })

    opportunities.sort(key=lambda o: (o["est_saving_high"] or o["over_benchmark"] or 0, o["spend"]), reverse=True)

    # Realism cap: total identified savings shouldn't exceed a sane share of total spend
    # (a generally-bloated cost base must not produce an absurd total / Score jump).
    total_spend = sum(float(l["amount"]) for l in lines)
    capped = False
    _cap = 0.25 * total_spend
    if _cap > 0 and total_high > _cap:
        _ratio = _cap / total_high if total_high else 1.0
        total_low = round(total_low * _ratio, 2)
        total_high = round(_cap, 2)
        capped = True

    return {
        "available": True,
        "total_expense_lines": len(lines),
        "total_est_saving_low": round(total_low, 2),
        "total_est_saving_high": round(total_high, 2),
        "total_est_saving_pct_of_revenue": round(total_high / revenue * 100, 2) if revenue else None,
        "capped_for_realism": capped,
        "opportunities": opportunities,
        "note": ("Deterministic spend-vs-benchmark + lower-cost-supplier suggestions. Savings are "
                 "indicative ranges off your actual spend at EQUIVALENT service — verify current quotes."),
        "disclaimer": "Switch only at matched service quality; figures are indicative and dated. "
                      "Decision-support; not a component of the Imara Score.",
    }
