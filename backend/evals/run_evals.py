"""
Paid full-pipeline eval runner. Runs each golden case through the LIVE pipeline
(consumes API credits) and prints a scorecard (coverage, faithfulness, band).
Usage:  cd backend && python -m evals.run_evals
The deterministic (no-API) ratio/extraction eval runs automatically in CI via
tests/test_evals.py — this runner is for the periodic quality check.
"""
import sys
from evals.grader import load_cases, grade_deterministic, grade_report


def main():
    cases = load_cases()
    print("=== Deterministic eval (no API) ===")
    for c in cases:
        d = grade_deterministic(c)
        print(f"  {d['name']:<28} ratios {d['ratios_computed']:>2}  checks {d['passed']}/{d['total']}  score {d['score']}")

    if "--full" not in sys.argv:
        print("\n(Add --full to also run the live pipeline and grade coverage/faithfulness — uses API credits.)")
        return

    from agents.ceo_agent import CEOAgent
    from memory.shared_memory import SharedMemory
    print("\n=== Full pipeline eval (LIVE — uses API) ===")
    for c in cases:
        m = SharedMemory()
        m.business_name = c["name"]; m.industry_key = c.get("industry_key", "general")
        m.currency = c.get("currency", "ZAR"); m.annual_revenue = c.get("annual_revenue", 0)
        m.uploaded_financial_text = c.get("financial_text", "")
        report = CEOAgent().run_full_analysis({"financial": {}}, m)
        g = grade_report(c, report)
        print(f"  {g['name']:<28} coverage {g['coverage_pass']}/{g['coverage_total']}  "
              f"conflicts {g['faithfulness_conflicts']}  band {g['imara_band']} ({'ok' if g['imara_band_ok'] else 'OUT OF RANGE'})  "
              f"runtime {report.get('total_runtime_seconds')}s")


if __name__ == "__main__":
    main()
