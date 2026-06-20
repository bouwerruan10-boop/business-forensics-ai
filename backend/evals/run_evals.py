"""
Eval runner. No-API graders (deterministic ratios + finding structure + SA
citation) run automatically in CI via tests/. This script also runs them
ad-hoc, and with --full runs the LIVE pipeline + LLM-as-judge (uses API).
Usage:  cd backend && python -m evals.run_evals [--full]
"""
import os
import sys

from evals.grader import (
    load_cases, grade_deterministic, grade_report,
    grade_structure, grade_sa_citation, grade_findings_with_judge, validate_judge, JUDGE_MODEL,
)


def _judge_call_factory():
    """Real judge call, pinned model. Lazy so no-API path needs no key."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def call(prompt: str) -> str:
        msg = client.messages.create(
            model=JUDGE_MODEL, max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    return call


def main():
    cases = load_cases()
    print("=== Deterministic eval (no API) ===")
    for c in cases:
        d = grade_deterministic(c)
        print(f"  {d['name']:<28} ratios {d['ratios_computed']:>2}  checks {d['passed']}/{d['total']}  score {d['score']}")

    if "--full" not in sys.argv:
        print("\n(Add --full to run the live pipeline + LLM-as-judge — uses API credits.)")
        return

    from agents.ceo_agent import CEOAgent
    from memory.shared_memory import SharedMemory
    judge = _judge_call_factory()
    vj = validate_judge(judge)
    print("\n=== Judge validation vs human labels (gate before trusting the judge) ===")
    print(f"  agreement {vj['agreement_pct']}% (target {vj['target']}) -> {'TRUSTWORTHY' if vj['trustworthy'] else 'NEEDS RUBRIC WORK'}")
    for r in vj["rows"]:
        if not r["agree"]:
            print(f"    disagree: {r['title']}  human={r['human']} judge={r['judge']}")
    print("\n=== Full pipeline eval (LIVE — uses API) ===")
    for c in cases:
        m = SharedMemory()
        m.business_name = c["name"]; m.industry_key = c.get("industry_key", "general")
        m.currency = c.get("currency", "ZAR"); m.annual_revenue = c.get("annual_revenue", 0)
        m.uploaded_financial_text = c.get("financial_text", "")
        report = CEOAgent().run_full_analysis({"financial": {}}, m)
        g = grade_report(c, report)
        st = grade_structure(report); sa = grade_sa_citation(report)
        jq = grade_findings_with_judge(report, judge)
        print(f"  {g['name']:<28} coverage {g['coverage_pass']}/{g['coverage_total']}  "
              f"conflicts {g['faithfulness_conflicts']}  band {g['imara_band']} ({'ok' if g['imara_band_ok'] else 'OUT'})")
        print(f"      structure {st['score']}  sa_cited {sa['score']}  judge {jq['overall_1to5']}/5 {jq['by_criterion']}")


if __name__ == "__main__":
    main()
