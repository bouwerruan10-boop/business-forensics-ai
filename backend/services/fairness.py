"""
Disparate-impact / fairness testing (deterministic, proxy-based).

The dossier (H1) and the model card both flagged that real disparate-impact testing was
"deferred until enough real outcomes accumulate". This module makes a real, if proxy-based,
fairness number available NOW from the analyses already on hand — the four-fifths (80%) rule
(EEOC) on the Imara band's selection rate across the only protected-adjacent proxies Imara
captures (industry, region/country). It does NOT use race/B-BBEE (excluded from the Score by
design); it surfaces an honest 'insufficient_data' until each group has a minimum sample.

This is a monitoring signal on the SCORE distribution, not a validated fairness audit of loan
outcomes (that needs real labelled defaults — Tier-0). Decision-support, never a guarantee.
"""

__all__ = ["disparate_impact", "fairness_report"]

# Bands treated as a "favourable" (likely-fundable) outcome for the selection-rate test.
_FAVOURABLE_BANDS = ("A", "B", "C")
_MIN_GROUP = 5            # below this per group -> not enough to compare (honest)
_FOUR_FIFTHS = 0.80


def _favourable(band, score, favourable_bands, score_threshold):
    b = str(band or "").strip().upper()[:1]
    if b in favourable_bands:
        return True
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        return score >= score_threshold
    return False


def disparate_impact(records, group_key, favourable_bands=_FAVOURABLE_BANDS,
                     score_threshold=50, min_group=_MIN_GROUP):
    """Four-fifths-rule disparate-impact over `records` grouped by `group_key`.

    records: iterable of dicts each with `group_key`, "imara_band" and/or "imara_score".
    Returns selection rate + mean score per qualifying group (n >= min_group), the adverse-impact
    ratio (min/max selection rate) and whether it passes the 80% rule. Pure; never raises.
    """
    if not isinstance(records, (list, tuple)):
        return {"available": False, "group_key": group_key, "reason": "No records."}
    buckets = {}
    for r in records:
        if not isinstance(r, dict):
            continue
        g = r.get(group_key)
        g = str(g).strip() if g not in (None, "") else None
        if not g:
            continue
        fav = _favourable(r.get("imara_band"), r.get("imara_score"), favourable_bands, score_threshold)
        sc = r.get("imara_score")
        b = buckets.setdefault(g, {"n": 0, "fav": 0, "score_sum": 0.0, "score_n": 0})
        b["n"] += 1
        b["fav"] += 1 if fav else 0
        if isinstance(sc, (int, float)) and not isinstance(sc, bool):
            b["score_sum"] += sc
            b["score_n"] += 1

    groups = []
    for g, b in buckets.items():
        if b["n"] < min_group:
            continue
        groups.append({
            "group": g, "n": b["n"],
            "selection_rate": round(b["fav"] / b["n"], 3),
            "mean_score": (round(b["score_sum"] / b["score_n"], 1) if b["score_n"] else None),
        })
    groups.sort(key=lambda x: x["selection_rate"])
    dropped = sum(1 for b in buckets.values() if b["n"] < min_group)

    if len(groups) < 2:
        return {"available": False, "group_key": group_key,
                "reason": "Need >= 2 groups each with >= %d analyses to compare (have %d)." % (min_group, len(groups)),
                "groups_below_min_sample": dropped}

    rates = [g["selection_rate"] for g in groups]
    means = [g["mean_score"] for g in groups if g["mean_score"] is not None]
    hi = max(rates)
    ratio = round(min(rates) / hi, 3) if hi > 0 else None
    return {
        "available": True,
        "group_key": group_key,
        "n_total": sum(g["n"] for g in groups),
        "groups": groups,
        "adverse_impact_ratio": ratio,            # min/max selection rate (the four-fifths statistic)
        "passes_four_fifths_rule": (ratio is not None and ratio >= _FOUR_FIFTHS),
        "mean_score_gap": (round(max(means) - min(means), 1) if len(means) >= 2 else None),
        "groups_below_min_sample": dropped,
        "method": ("EEOC four-fifths rule: lowest group selection rate / highest. >= 0.80 passes. "
                   "'Favourable' = Imara band in %s or score >= %d." % (list(favourable_bands), score_threshold)),
        "disclaimer": ("Proxy-based monitoring of the Score distribution across %s — NOT a validated "
                       "fairness audit of loan outcomes (that needs real labelled defaults). Race / "
                       "B-BBEE is excluded from the Score by design." % group_key),
    }


def fairness_report(reports=None):
    """Run disparate-impact across the captured proxies (industry, region/country).

    `reports` = list of report dicts; if None, pulls recent_reports() from the DB.
    """
    if reports is None:
        try:
            from services.database import recent_reports
            reports = [r.get("report") or {} for r in recent_reports(limit=500)]
        except Exception:
            reports = []
    rows = []
    for rep in reports:
        if not isinstance(rep, dict):
            continue
        rows.append({"imara_band": rep.get("imara_band"), "imara_score": rep.get("imara_score"),
                     "industry": rep.get("industry"), "region": rep.get("country")})
    return {
        "available": True,
        "sample_size": len(rows),
        "industry": disparate_impact(rows, "industry"),
        "region": disparate_impact(rows, "region"),
        "basis": "Four-fifths-rule disparate impact on the Imara band across the proxies Imara captures.",
        "disclaimer": ("Score-distribution monitoring, not an outcome-validated fairness audit. "
                       "Real disparate-impact on funding/repayment needs labelled outcomes (Tier-0)."),
    }
