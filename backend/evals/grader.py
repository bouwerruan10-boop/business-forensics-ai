"""
Eval grader — Phase 0 of the improvement plan.

Two grading levels:
  * grade_deterministic(case) — NO API. Runs the extraction + ratio engine on a
    golden case and checks the computed ratios/statuses against known-correct
    expectations. This is the regression guard that would have caught the
    live-test extraction bug, and it runs in CI on every change.
  * grade_report(case, report) — grades a FULL pipeline output (needs an API run):
    coverage of planted issues, faithfulness (zero conflicts), and that the Imara
    band lands in the expected range.
"""
import glob
import json
import os

from services.financial_ratios import extract_financials, compute_ratios, fundamentals_score

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")


def load_cases():
    cases = []
    for path in sorted(glob.glob(os.path.join(GOLDEN_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            cases.append(json.load(fh))
    return cases


def _tol(expected):
    # 5% relative, or 0.5 absolute floor (whichever is larger)
    return max(0.5, abs(expected) * 0.05)


def grade_deterministic(case: dict) -> dict:
    """No-API: extraction + ratio correctness for one golden case."""
    figs = extract_financials(case.get("financial_text", ""))
    ratios = compute_ratios(figs, case.get("industry_key", "general"), case.get("annual_revenue", 0))
    checks = []
    for key, expected in case.get("expected_ratios", {}).items():
        got = ratios.get(key, {}).get("value")
        ok = got is not None and abs(got - expected) <= _tol(expected)
        checks.append({"check": "ratio:" + key, "expected": expected, "got": got, "pass": bool(ok)})
    for key, status in case.get("expected_status", {}).items():
        got = ratios.get(key, {}).get("status")
        checks.append({"check": "status:" + key, "expected": status, "got": got, "pass": got == status})
    passed = sum(1 for c in checks if c["pass"])
    total = len(checks)
    return {
        "name": case.get("name", "?"),
        "checks": checks,
        "passed": passed,
        "total": total,
        "score": round(passed / total * 100) if total else 100,
        "ratios_computed": len(ratios),
        "fundamentals": fundamentals_score(ratios, case.get("industry_key", "general")).get("score"),
    }


def _all_findings_text(report: dict) -> str:
    parts = []
    for lst in (report.get("department_findings", {}) or {}).values():
        for f in lst:
            parts.append((f.get("title", "") or "") + " " + (f.get("detail", "") or ""))
    return " ".join(parts).lower()


def grade_report(case: dict, report: dict) -> dict:
    """Full-pipeline grade: coverage + faithfulness + Imara band sanity."""
    text = _all_findings_text(report)
    coverage = [{"issue": kw, "covered": kw.lower() in text} for kw in case.get("planted_issues", [])]
    cov_pass = sum(1 for c in coverage if c["covered"])
    cov_total = len(coverage)
    faith = report.get("faithfulness_summary", {}) or {}
    conflicts = int(faith.get("conflicts", 0) or 0)
    band = report.get("imara_band")
    band_range = case.get("imara_band_in", [])
    band_ok = (band in band_range) if band_range else True
    return {
        "name": case.get("name", "?"),
        "coverage": coverage,
        "coverage_pass": cov_pass,
        "coverage_total": cov_total,
        "faithfulness_conflicts": conflicts,
        "imara_band": band,
        "imara_band_ok": band_ok,
        "ok": (cov_pass == cov_total) and band_ok,  # conflicts reported, not auto-fail
    }


def deterministic_report(cases=None) -> dict:
    cases = cases or load_cases()
    results = [grade_deterministic(c) for c in cases]
    overall = round(sum(r["score"] for r in results) / len(results)) if results else 100
    return {"overall_score": overall, "results": results}


# ── Build 2: quality eval framework ────────────────────────────────────────
# Two no-API graders (CI regression gates) + one LLM-as-judge semantic grader
# (paid; injected judge_call for testability). See evals/RUBRIC.md.
import re as _re

_ZAR = _re.compile(r"R\s?\d", _re.I)
_ACT = _re.compile(r"Act\s+\d+\s+of\s+\d{4}|\bs\s?\d+\b|section\s+\d+|Schedule", _re.I)

# Pin BOTH agent and judge model versions so a silent provider update is detected.
JUDGE_MODEL = "claude-sonnet-4-6"


def _iter_findings(report: dict):
    for lst in (report.get("department_findings", {}) or {}).values():
        for f in (lst or []):
            yield f


def grade_structure(report: dict) -> dict:
    """NO-API: fraction of findings satisfying the FINDING_RULES output contract.
    A regression gate on finding quality — catches prompt drift that drops ZAR
    quantification, recommendations, or benchmarks."""
    findings = list(_iter_findings(report))
    if not findings:
        return {"findings": 0, "score": 0, "pct": {}}

    def has(f, k):
        return bool((f.get(k) or "").strip())

    crit = {
        "has_financial_impact": lambda f: has(f, "financial_impact"),
        "quantified_zar": lambda f: bool(_ZAR.search((f.get("financial_impact", "") or "") + " " + (f.get("detail", "") or ""))),
        "has_recommendation": lambda f: has(f, "recommendation"),
        "valid_severity": lambda f: f.get("severity") in ("critical", "high", "medium", "low"),
        "has_benchmark": lambda f: has(f, "benchmark_reference"),
    }
    n = len(findings)
    pct = {name: round(sum(1 for f in findings if fn(f)) / n * 100) for name, fn in crit.items()}
    return {"findings": n, "score": round(sum(pct.values()) / len(pct)), "pct": pct}


def grade_sa_citation(report: dict) -> dict:
    """NO-API: fraction of SA tax/legal findings that cite a specific Act/section.
    Directly measures whether the RAG grounding (Build 1) is taking effect."""
    sa = []
    for f in _iter_findings(report):
        a = (f.get("agent", "") or "").lower()
        if any(t in a for t in ("sa ", "satax", "salegal", "tax", "legal", "bbbee")):
            sa.append(f)
    if not sa:
        return {"sa_findings": 0, "cited": 0, "score": None}
    cited = sum(1 for f in sa if _ACT.search(" ".join(
        (f.get(k, "") or "") for k in ("detail", "recommendation", "benchmark_reference", "title"))))
    return {"sa_findings": len(sa), "cited": cited, "score": round(cited / len(sa) * 100)}


RUBRIC_CRITERIA = ("specificity", "actionability", "grounding", "severity_fit")


def build_judge_prompt(finding: dict) -> str:
    """Prompt for the LLM-as-judge. Reference-free, rubric-based (1-5 each)."""
    return (
        "You are a strict QA reviewer of a South African SME advisory finding. "
        "Score the finding from 1 (poor) to 5 (excellent) on each criterion:\n"
        "- specificity: cites concrete figures/dates/thresholds, not vague generalities\n"
        "- actionability: the recommendation is concrete and a business owner could act on it\n"
        "- grounding: claims are tied to the data or cited law; no fabricated facts\n"
        "- severity_fit: the severity label matches the stated financial impact\n\n"
        "FINDING:\n"
        "title: {title}\nseverity: {severity}\ndetail: {detail}\n"
        "financial_impact: {fi}\nrecommendation: {rec}\nbenchmark_reference: {bench}\n\n"
        'Return ONLY JSON: {{"specificity":n,"actionability":n,"grounding":n,"severity_fit":n,"comment":"<=15 words"}}'
    ).format(
        title=finding.get("title", ""), severity=finding.get("severity", ""),
        detail=finding.get("detail", ""), fi=finding.get("financial_impact", ""),
        rec=finding.get("recommendation", ""), bench=finding.get("benchmark_reference", ""),
    )


def grade_findings_with_judge(report: dict, judge_call, sample: int = 8) -> dict:
    """LLM-as-judge semantic quality. `judge_call(prompt:str)->str` returns the
    judge's JSON text (injected so this is testable offline and pins the model
    in the paid runner). Averages 1-5 scores across a sampled set of findings."""
    findings = list(_iter_findings(report))[:sample]
    scored, per_crit = [], {c: [] for c in RUBRIC_CRITERIA}
    for f in findings:
        try:
            raw = judge_call(build_judge_prompt(f))
            data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        except Exception:
            continue
        if all(c in data for c in RUBRIC_CRITERIA):
            scored.append(data)
            for c in RUBRIC_CRITERIA:
                per_crit[c].append(float(data[c]))
    avg = {c: round(sum(v) / len(v), 2) for c, v in per_crit.items() if v}
    overall = round(sum(avg.values()) / len(avg), 2) if avg else None
    return {"judged": len(scored), "by_criterion": avg, "overall_1to5": overall}


def quality_report(report: dict) -> dict:
    """No-API quality snapshot (structure + SA citation) for CI + ops."""
    return {"structure": grade_structure(report), "sa_citation": grade_sa_citation(report)}
