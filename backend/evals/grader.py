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
