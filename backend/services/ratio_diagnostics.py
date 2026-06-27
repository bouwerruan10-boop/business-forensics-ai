"""
ratio_diagnostics.py - deterministic "ratio -> what it means -> what to do" join.

Links each computed financial ratio (from financial_ratios) to a plain-language
explanation, the findings that reference it, and the simulator action that
closes its gap (from simulation.derive_actions). Everything is computed in code;
the dashboard only renders it. No LLM, no new figures invented.
"""

from services.simulation import derive_actions

# which simulator action id improves which ratio
_ACTION_FOR_RATIO = {
    "gross_margin": "gross_margin",
    "operating_margin": "opex",
    "debtor_days": "debtor_days",
    "inventory_days": "inventory_days",
}

_STATUS_ORDER = {"critical": 0, "warning": 1, "good": 2}

_STATUS_PHRASE = {
    "good": "at or better than the sector benchmark - a strength.",
    "warning": "off the sector benchmark - worth watching.",
    "critical": "well off the sector benchmark - a priority to fix.",
}


def _fmt(value, unit):
    if value is None:
        return "n/a"
    u = (unit or "").strip()
    if u == "%":
        return "{:,.1f}%".format(value)
    if u:
        return "{:,.1f} {}".format(value, u)
    return "{:,.2f}".format(value)


def _plain(label, value, unit, benchmark, status):
    here = _fmt(value, unit)
    if benchmark is None:
        return "Your {} is {}.".format(label, here)
    return "Your {} ({}) is {}".format(
        label, here, _STATUS_PHRASE.get(status, "compared to a sector benchmark of {}.".format(_fmt(benchmark, unit))),
    ) + (" (benchmark {}).".format(_fmt(benchmark, unit)) if status in _STATUS_PHRASE else "")


def build_diagnostics(report):
    """Return {diagnostics: [...], count} joining ratios -> meaning -> action -> findings."""
    report = report if isinstance(report, dict) else {}
    ratios = report.get("financial_ratios")
    ratios = ratios if isinstance(ratios, dict) else {}

    try:
        actions = {a.get("id"): a for a in derive_actions(report) if isinstance(a, dict)}
    except Exception:
        actions = {}

    findings = report.get("all_findings_ranked")
    findings = findings if isinstance(findings, list) else []

    rows = []
    for key, r in ratios.items():
        if not isinstance(r, dict) or r.get("value") is None:
            continue
        value, bench = r.get("value"), r.get("benchmark")
        unit, status = r.get("unit"), r.get("status")
        label = r.get("label") or key.replace("_", " ").title()

        gap = None
        if isinstance(value, (int, float)) and isinstance(bench, (int, float)):
            gap = round(value - bench, 2)

        act = actions.get(_ACTION_FOR_RATIO.get(key))
        recommendation = None
        if isinstance(act, dict):
            recommendation = {
                "label": act.get("label"),
                "rationale": act.get("rationale"),
                "max": act.get("max"),
                "unit": act.get("unit"),
            }

        kw = key.replace("_", " ")
        linked = [
            f.get("title") for f in findings
            if isinstance(f, dict)
            and kw in (str(f.get("category", "")) + " " + str(f.get("title", ""))).lower()
        ]

        rows.append({
            "key": key,
            "label": label,
            "value": value,
            "unit": unit,
            "benchmark": bench,
            "gap": gap,
            "status": status,
            "plain_meaning": _plain(label, value, unit, bench, status),
            "recommendation": recommendation,
            "linked_findings": [t for t in linked if t][:3],
        })

    rows.sort(key=lambda x: _STATUS_ORDER.get(x["status"], 3))
    return {"diagnostics": rows, "count": len(rows)}
