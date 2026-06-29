"""
Validation harness — turns scores + labels into the standard discrimination and
calibration evidence a lender/regulator expects. Pure Python (no sklearn), no LLM.

Two evidence paths:
  1. REAL outcomes  — once funding/repayment/default labels are recorded (outcomes
     table), measure how well the Imara Score separates good from bad: AUC / Gini / KS
     + a reliability table (bad-rate per score band).
  2. Z'' PROXY backtest — available NOW from existing analyses: treat the INDEPENDENT
     Altman Z'' distress zone as a proxy "bad" label and measure how well the Imara
     Score discriminates it. Convergent-validity evidence today, clearly labelled a
     proxy (not real outcomes).

Honest by construction: returns {available: False, reason} until there is enough data,
and never overclaims (a proxy backtest is reported as a proxy).
"""

# Imara Score is 0-100 where HIGHER = better/safer. Risk = 100 - score.

def _auc(scores, labels):
    """AUC for predicting label=1 (bad) from RISK = 100 - score, via the rank method
    (== Mann-Whitney U). Returns None if a class is empty."""
    pairs = [(100.0 - float(s), int(l)) for s, l in zip(scores, labels)]
    n_pos = sum(1 for _, l in pairs if l == 1)
    n_neg = len(pairs) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    # average ranks (ascending by risk)
    order = sorted(range(len(pairs)), key=lambda i: pairs[i][0])
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and pairs[order[j + 1]][0] == pairs[order[i]][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # 1-based average rank
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    sum_ranks_pos = sum(ranks[i] for i in range(len(pairs)) if pairs[i][1] == 1)
    return (sum_ranks_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def _ks(scores, labels):
    """KS statistic: max gap between cumulative good and bad distributions across score."""
    rows = sorted(zip((float(s) for s in scores), (int(l) for l in labels)), key=lambda x: x[0])
    n_bad = sum(l for _, l in rows)
    n_good = len(rows) - n_bad
    if n_bad == 0 or n_good == 0:
        return None
    cb = cg = 0
    ks = 0.0
    for _, l in rows:
        if l == 1:
            cb += 1
        else:
            cg += 1
        ks = max(ks, abs(cb / n_bad - cg / n_good))
    return ks


def _reliability(scores, labels, bands=((0, 35), (35, 50), (50, 65), (65, 80), (80, 101))):
    """Bad-rate per Imara band — should fall as the score rises (monotonic = well-ranked)."""
    out = []
    for lo, hi in bands:
        grp = [int(l) for s, l in zip(scores, labels) if lo <= float(s) < hi]
        if grp:
            out.append({"band": "{}-{}".format(lo, hi - 1 if hi <= 100 else 100),
                        "n": len(grp), "bad_rate": round(sum(grp) / len(grp), 3)})
    return out


def discrimination(pairs: list) -> dict:
    """pairs: [{imara_score, label}] (label 1=bad/default). Returns AUC/Gini/KS + reliability."""
    pairs = [p for p in pairs if p.get("imara_score") is not None and p.get("label") in (0, 1)]
    n = len(pairs)
    n_bad = sum(p["label"] for p in pairs)
    if n < 20 or n_bad == 0 or n_bad == n:
        return {"available": False,
                "reason": "Need >= 20 labelled cases with both outcomes (have {}, {} bad).".format(n, n_bad),
                "n": n, "n_bad": n_bad}
    scores = [p["imara_score"] for p in pairs]
    labels = [p["label"] for p in pairs]
    auc = _auc(scores, labels)
    return {
        "available": True, "n": n, "n_bad": n_bad,
        "auc": round(auc, 3) if auc is not None else None,
        "gini": round(2 * auc - 1, 3) if auc is not None else None,
        "ks": round(_ks(scores, labels), 3),
        "reliability": _reliability(scores, labels),
    }


def zscore_proxy_backtest(reports: list) -> dict:
    """Use the independent Altman Z'' distress zone as a PROXY bad label and measure how
    well the Imara Score discriminates it. reports: [{report: {...}}] or [report]."""
    pairs = []
    for r in reports:
        rep = r.get("report") if isinstance(r, dict) and "report" in r else r
        if not isinstance(rep, dict):
            continue
        sc = rep.get("imara_score")
        z = rep.get("distress_score") or {}
        if sc is None or not z.get("available"):
            continue
        pairs.append({"imara_score": sc, "label": 1 if z.get("zone") == "distress" else 0})
    res = discrimination(pairs)
    res["proxy"] = "Altman Z'' distress zone (independent model) — convergent-validity proxy, NOT real outcomes"
    res["analyses_with_zscore"] = len(pairs)
    return res


_PSI_BANDS = ((0, 35), (35, 50), (50, 65), (65, 80), (80, 101))


def _band_pcts(scores, bands):
    if not isinstance(scores, (list, tuple)):
        return None, 0
    vals = [float(s) for s in scores if isinstance(s, (int, float)) and not isinstance(s, bool)]
    n = len(vals)
    if not n:
        return None, 0
    pcts = []
    for lo, hi in bands:
        c = sum(1 for v in vals if lo <= v < hi)
        pcts.append(c / n)
    return pcts, n


def psi(baseline_scores, recent_scores, bands=_PSI_BANDS, min_each=20) -> dict:
    """Population Stability Index between a baseline and a recent score distribution.

    PSI = sum( (recent% - base%) * ln(recent% / base%) ) across score bands.
    < 0.10 stable · 0.10-0.25 moderate shift · >= 0.25 significant shift. Pure; never raises.
    Empty bins are floored to a small epsilon so the log stays finite.
    """
    import math
    base_pcts, n_base = _band_pcts(baseline_scores, bands)
    recent_pcts, n_recent = _band_pcts(recent_scores, bands)
    if base_pcts is None or recent_pcts is None or n_base < min_each or n_recent < min_each:
        return {"available": False,
                "reason": "Need >= {} scores in each window (have {} baseline, {} recent).".format(
                    min_each, n_base, n_recent)}
    eps = 1e-4
    rows, total = [], 0.0
    for (lo, hi), b, r in zip(bands, base_pcts, recent_pcts):
        bb, rr = max(b, eps), max(r, eps)
        contrib = (rr - bb) * math.log(rr / bb)
        total += contrib
        rows.append({"band": "{}-{}".format(lo, hi - 1 if hi <= 100 else 100),
                     "baseline_pct": round(b, 3), "recent_pct": round(r, 3),
                     "contribution": round(contrib, 4)})
    interp = ("stable" if total < 0.10 else "moderate_shift" if total < 0.25 else "significant_shift")
    return {"available": True, "psi": round(total, 4), "interpretation": interp,
            "n_baseline": n_base, "n_recent": n_recent, "bands": rows,
            "note": "PSI on the Imara Score distribution (population drift). < 0.10 stable; >= 0.25 significant."}


def realised_vs_predicted(pairs: list, bands=_PSI_BANDS) -> dict:
    """Per-band realised bad-rate vs the rate the score-band implies (mid-band risk = 100 - mid-score).
    A monotonic, close match = well-calibrated ranking. pairs: [{imara_score, label}]. Pure."""
    pairs = [p for p in pairs if p.get("imara_score") is not None and p.get("label") in (0, 1)]
    if len(pairs) < 20:
        return {"available": False, "reason": "Need >= 20 labelled cases (have {}).".format(len(pairs))}
    rows = []
    for lo, hi in bands:
        grp = [int(p["label"]) for p in pairs if lo <= float(p["imara_score"]) < hi]
        if grp:
            implied = round((100 - (lo + min(hi, 100)) / 2.0) / 100.0, 3)   # mid-band risk
            rows.append({"band": "{}-{}".format(lo, hi - 1 if hi <= 100 else 100), "n": len(grp),
                         "realised_bad_rate": round(sum(grp) / len(grp), 3), "implied_bad_rate": implied})
    return {"available": True, "n": len(pairs), "bands": rows,
            "note": "Realised default rate per Imara band vs the band's implied risk; monotonic falling = well-ranked."}


def validation_report(outcome_pairs: list, reports: list) -> dict:
    """Combined evidence: real-outcome discrimination (if any) + the Z''-proxy backtest."""
    return {
        "real_outcomes": discrimination(outcome_pairs),
        "realised_vs_predicted": realised_vs_predicted(outcome_pairs),
        "zscore_proxy": zscore_proxy_backtest(reports),
        "note": ("Discrimination on REAL funding/repayment outcomes is the goal (collect via the "
                 "design-partner pilot). Until then the Z'' proxy gives convergent-validity evidence. "
                 "AUC 0.5 = no skill, 0.7+ = useful, 0.8+ = strong; Gini = 2*AUC-1."),
    }
