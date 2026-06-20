"""
Fleet quality — ONLINE evaluation for Imara.

Offline evals (golden set + judge) catch known regressions before deploy.
This is the complementary ONLINE layer: it aggregates the quality signals Imara
ALREADY computes on every real analysis (faithfulness conflicts, finding-quality
mix, cost, extraction source, score/band, runtime) across the persisted analyses
into a fleet view, and flags DRIFT — a recent window vs the prior baseline — so a
silent model update, odd inputs, or a quality regression on real traffic surface
early. Cheap: the per-run signals exist already; this only reads + aggregates.
"""


def extract_metrics(report: dict) -> dict:
    """Compact per-run quality signals pulled from a finished report."""
    f = report.get("faithfulness_summary") or {}
    fq = report.get("finding_quality") or {}
    usage = report.get("llm_usage") or {}
    dc = report.get("document_coverage") or {}
    return {
        "imara_score": report.get("imara_score"),
        "imara_band": report.get("imara_band"),
        "conflicts": int(f.get("conflicts") or 0),
        "checked": int(f.get("checked") or 0),
        "strong_pct": fq.get("strong_pct"),
        "weak": int(fq.get("weak") or 0),
        "findings_total": fq.get("total") if fq.get("total") is not None else report.get("total_findings"),
        "est_cost_usd": usage.get("est_cost_usd"),
        "calls": usage.get("calls"),
        "extraction_source": report.get("financial_extraction_source") or "deterministic",
        "runtime_seconds": report.get("total_runtime_seconds"),
        "macro_exposure": report.get("macro_overall_exposure") or None,
        "doc_types": (sum(1 for v in dc.values() if v) if dc else None),
    }


def _avg(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 2) if vals else None


def _summarise(metrics_list):
    n = len(metrics_list)
    if not n:
        return {}
    conflict_runs = sum(1 for m in metrics_list if (m.get("conflicts") or 0) > 0)
    ai_runs = sum(1 for m in metrics_list if m.get("extraction_source") == "ai")
    return {
        "runs": n,
        "avg_imara_score": _avg([m.get("imara_score") for m in metrics_list]),
        "avg_strong_pct": _avg([m.get("strong_pct") for m in metrics_list]),
        "conflict_rate_pct": round(conflict_runs / n * 100),
        "ai_extraction_rate_pct": round(ai_runs / n * 100),
        "avg_cost_usd": _avg([m.get("est_cost_usd") for m in metrics_list]),
        "avg_runtime_s": _avg([m.get("runtime_seconds") for m in metrics_list]),
    }


def _drift(recent, baseline):
    """Flag metrics whose recent-window value diverges from the baseline."""
    alerts = []
    if not recent.get("runs") or not baseline.get("runs"):
        return alerts
    checks = [
        ("avg_imara_score", 8, "Average Imara Score"),
        ("conflict_rate_pct", 15, "Faithfulness-conflict rate"),
        ("avg_strong_pct", 15, "Strong-findings %"),
        ("ai_extraction_rate_pct", 25, "AI-extraction rate"),
    ]
    for key, thresh, label in checks:
        r, b = recent.get(key), baseline.get(key)
        if isinstance(r, (int, float)) and isinstance(b, (int, float)) and abs(r - b) >= thresh:
            alerts.append({"metric": key, "label": label, "recent": r, "baseline": b,
                           "delta": round(r - b, 2)})
    # cost spike: recent avg > 1.5x baseline
    rc, bc = recent.get("avg_cost_usd"), baseline.get("avg_cost_usd")
    if isinstance(rc, (int, float)) and isinstance(bc, (int, float)) and bc > 0 and rc >= 1.5 * bc:
        alerts.append({"metric": "avg_cost_usd", "label": "Average cost/run", "recent": rc,
                       "baseline": bc, "delta": round(rc - bc, 4)})
    return alerts


def aggregate(records: list, recent_window: int = 8) -> dict:
    """records: [{created_at, metrics}], most-recent first. Returns fleet summary,
    band distribution, extraction mix, and drift alerts (recent vs baseline)."""
    metrics = [r["metrics"] for r in records]
    overall = _summarise(metrics)
    bands = {}
    for m in metrics:
        b = m.get("imara_band")
        if b:
            bands[b] = bands.get(b, 0) + 1
    recent = _summarise(metrics[:recent_window])
    baseline = _summarise(metrics[recent_window:])
    alerts = _drift(recent, baseline)
    return {
        "overall": overall,
        "band_distribution": bands,
        "recent": recent,
        "baseline": baseline,
        "drift_alerts": alerts,
        "healthy": len(alerts) == 0,
        "window": recent_window,
    }
