"""
Deterministic finding self-critique (no API, no extra cost).

After the agents produce findings, this layer grades each one against Imara's
own FINDING_RULES contract and attaches per-finding quality flags + a tier
(strong / adequate / weak). It is the deterministic counterpart to the paid
LLM-as-judge in evals/grader.py: it runs on every production report (free,
instant, reproducible), gives the operator an honest "which findings are soft"
signal, and is a hook the dashboard can render as badges. It strengthens trust
without ever fabricating content — consistent with Imara's anti-hallucination DNA.

The LLM self-reflection variant and structured-outputs (dropping the 2nd parse
call) are the next agent-architecture rungs, but both change live API behaviour
and must be validated on a real run before activation.
"""
import re

# Currency presence (R / ZAR / rand followed by a figure somewhere).
_ZAR = re.compile(r"(R\s?\d|\bZAR\b\s*\d|\d[\d ,.]*\s*(rand|zar))", re.I)
_GENERIC_BENCH = {"", "n/a", "na", "none", "see analysis above", "see analysis", "tbd", "uploaded data"}
_GENERIC_REC = {"", "review this area with management team", "review with management", "tbd with client"}


def _has_zar(*parts) -> bool:
    text = " ".join(p or "" for p in parts)
    return bool(_ZAR.search(text))


def critique_finding(f: dict):
    """Return (flags, quality_tier) for one finding dict."""
    fi = (f.get("financial_impact") or "").strip()
    detail = (f.get("detail") or "").strip()
    rec = (f.get("recommendation") or "").strip()
    bench = (f.get("benchmark_reference") or "").strip()
    coi = (f.get("cost_of_inaction") or "").strip()
    sev = f.get("severity")

    quantified = _has_zar(fi, detail) and "unquantified" not in fi.lower()

    flags = []
    if not quantified:
        flags.append("unquantified")
    if len(rec.split()) < 4 or rec.lower() in _GENERIC_REC:
        flags.append("vague_recommendation")
    if bench.lower() in _GENERIC_BENCH:
        flags.append("no_benchmark")
    if not coi:
        flags.append("no_cost_of_inaction")
    # A finding flagged critical/high but with no quantified impact is the most
    # important soft signal — its urgency is unsupported by numbers.
    if sev in ("critical", "high") and not quantified:
        flags.append("severity_impact_mismatch")

    if not flags:
        quality = "strong"
    elif "severity_impact_mismatch" in flags or len(flags) >= 3:
        quality = "weak"
    else:
        quality = "adequate"
    return flags, quality


def critique_report(report: dict) -> dict:
    """Attach `quality_flags` + `quality` to every finding (in both the
    department_findings and all_findings_ranked views) and return a summary.
    Idempotent: flags are assigned, not appended, so re-running is safe."""
    summary = {"total": 0, "strong": 0, "adequate": 0, "weak": 0, "by_flag": {}}
    seen = set()
    buckets = list((report.get("department_findings") or {}).values())
    buckets.append(report.get("all_findings_ranked") or [])
    for lst in buckets:
        for f in (lst or []):
            flags, quality = critique_finding(f)
            f["quality_flags"] = flags
            f["quality"] = quality
            if id(f) in seen:  # count each unique finding once
                continue
            seen.add(id(f))
            summary["total"] += 1
            summary[quality] += 1
            for fl in flags:
                summary["by_flag"][fl] = summary["by_flag"].get(fl, 0) + 1
    summary["strong_pct"] = round(summary["strong"] / summary["total"] * 100) if summary["total"] else None
    return summary
