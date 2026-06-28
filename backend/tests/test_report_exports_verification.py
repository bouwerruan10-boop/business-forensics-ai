"""The PDF + HTML exporters carry the 'prove it' verification/evidence contract onto the
artifact the recipient receives (lender/investor), and omit it cleanly when absent."""
from services.html_report import generate_html_report
from services.report_generator import generate_pdf_report, _verification_section
from services.claim_ledger import build_claim_ledger

_BASE = {
    "business_name": "Acme (Pty) Ltd", "industry": "retail", "currency": "ZAR", "annual_revenue": 5_000_000,
    "imara_score": 58, "imara_band": "B", "imara_label": "Moderate", "imara_color": "#C9820A",
    "imara_components": [], "executive_summary": "x", "situation": "s", "complication": "c", "resolution": "r",
    "all_findings_ranked": [], "department_findings": {}, "quick_wins": [], "top_priority_issues": [],
    "financial_ratios": {}, "scores": {}, "valuation_mid": 2_000_000, "valuation_low": 1_500_000,
    "valuation_high": 2_800_000, "credit_score": 60, "credit_grade": "B", "implementation_roadmap": [],
}

# A report whose narrative carries a real conflict (21.3% vs computed 33.2%) + an untraceable estimate.
_REP = {**_BASE,
        "financial_ratios": {"gross_margin": {"value": 33.2, "label": "gross margin"}},
        "financial_figures": {"net_profit": 450_000},
        "executive_summary": "Gross margin is 21.3% and net profit was R450,000. An upside of R1.2 million exists.",
        "department_findings": {"Fin": [{"title": "Drain", "financial_impact": "R450,000 drain",
                                          "cost_of_inaction": "R2,000,000 at risk"}]}}
_REP = {**_REP, "claim_ledger": build_claim_ledger(_REP)}


def _ledger(overall, claims):
    return {"available": True, "overall": overall, "headline": "h",
            "assurance": {"coverage_pct": 50.0, "avg_confidence": 0.6, "statement": "stmt"},
            "narrative_claims": claims, "finding_figure_claims": []}


# ── PDF ──

def test_pdf_includes_verification_when_ledger_present():
    pdf = generate_pdf_report(_REP, audience="banker")
    assert pdf[:4] == b"%PDF" and len(pdf) > 1000
    story = []
    _verification_section(story, _REP)
    assert len(story) > 0                       # section actually rendered flowables


def test_pdf_safe_without_ledger():
    assert generate_pdf_report(dict(_BASE), audience="banker")[:4] == b"%PDF"


def test_pdf_robust_to_hostile_ledger():
    for bad in ("x", None, {"available": False}, {"available": True}):
        assert generate_pdf_report({**_BASE, "claim_ledger": bad}, audience="owner")[:4] == b"%PDF"


# ── HTML ──

def test_html_includes_verification_and_state():
    h = generate_html_report(_REP)
    assert "Every number, checked against your data" in h
    assert "NEEDS REVIEW" in h                   # a conflict is present
    assert "% traced to computed data" in h


def test_html_omits_when_absent():
    assert "Every number, checked against your data" not in generate_html_report(dict(_BASE))


def test_html_state_labels():
    verified = generate_html_report({**_BASE, "claim_ledger": _ledger("all_clear", [])})
    estimates = generate_html_report({**_BASE, "claim_ledger": _ledger(
        "unverified_present", [{"text": "R2m", "verification": "unverified"}])})
    review = generate_html_report({**_BASE, "claim_ledger": _ledger(
        "conflicts_present", [{"text": "21.3%", "verification": "conflict", "explanation": "vs 33.2%"}])})
    assert ">VERIFIED<" in verified
    assert "SOME ESTIMATES" in estimates
    assert "NEEDS REVIEW" in review


def test_html_escapes_injection_in_claim_text():
    hostile = _ledger("conflicts_present", [{"text": "<script>alert(1)</script>",
                                             "verification": "conflict", "explanation": "<b>x</b>"}])
    h = generate_html_report({**_BASE, "claim_ledger": hostile})
    assert "<script>alert(1)</script>" not in h and "&lt;script&gt;" in h


def test_html_robust_to_hostile_ledger():
    for bad in ("x", None, {"available": False}):
        assert isinstance(generate_html_report({**_BASE, "claim_ledger": bad}), str)
