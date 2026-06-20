"""
Supplier benchmarking engine — turns extracted expense line items into spend-vs-
benchmark assessments (Layer A) and lower-cost-supplier opportunities (Layer B).

All deterministic. Savings are indicative RANGES off the firm's actual spend at
EQUIVALENT service, each dated + sourced. Never invents a competitor's exact price;
never feeds the Imara Score (decision-support / opportunity only). Feeds the Action
Simulator's opex lever so the user can see the projected Score uplift if they act.
"""

from services.expense_lines import extract_expense_lines
from services.supplier_catalog import category_reference


def run_supplier_benchmark(financial_text: str, revenue, profile=None, bank_signals=None) -> dict:
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
        incumbent = profile.get("banking_partner") if (cat == "bank_charges" and banking_partner) else None
        save_low = save_high = None
        confidence = "low"
        if line.get("substitutable") and providers and sav:
            sl, sh = sav
            incumbent_higher = bool(incumbent) and any(
                h in incumbent.lower() for h in ref.get("higher_cost_incumbents", []))
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

    return {
        "available": True,
        "total_expense_lines": len(lines),
        "total_est_saving_low": round(total_low, 2),
        "total_est_saving_high": round(total_high, 2),
        "total_est_saving_pct_of_revenue": round(total_high / revenue * 100, 2) if revenue else None,
        "opportunities": opportunities,
        "note": ("Deterministic spend-vs-benchmark + lower-cost-supplier suggestions. Savings are "
                 "indicative ranges off your actual spend at EQUIVALENT service — verify current quotes."),
        "disclaimer": "Switch only at matched service quality; figures are indicative and dated. "
                      "Decision-support; not a component of the Imara Score.",
    }
