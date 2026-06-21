"""The PDF + HTML exporters include the Tax Me If You Can section when available,
and omit it cleanly otherwise."""
from services.html_report import generate_html_report
from services.report_generator import generate_pdf_report

_BASE = {
    "business_name": "Acme (Pty) Ltd", "industry": "retail", "currency": "ZAR", "annual_revenue": 5_000_000,
    "imara_score": 58, "imara_band": "B", "imara_label": "Moderate", "imara_color": "#C9820A",
    "imara_components": [], "executive_summary": "x", "situation": "s", "complication": "c", "resolution": "r",
    "all_findings_ranked": [], "department_findings": {}, "quick_wins": [], "top_priority_issues": [],
    "financial_ratios": {}, "scores": {}, "valuation_mid": 2_000_000, "valuation_low": 1_500_000,
    "valuation_high": 2_800_000, "credit_score": 60, "credit_grade": "B", "implementation_roadmap": [],
}
_TX = {"available": True, "currency": "ZAR", "as_of": "2026-06-21", "sbc_tax_year": "2025/26",
       "total_saving_low": 81802, "total_saving_high": 81802, "quantified_count": 1,
       "summary": "1 relief identified.", "disclaimer": "Not tax advice.",
       "opportunities": [{"name": "Small Business Corporation rates (Section 12E)", "eligible": "likely",
                          "quantified": True, "est_saving_low": 81802, "est_saving_high": 81802,
                          "basis": "Turnover <= R20m.", "action": "Apply Section 12E.", "caveat": "Verify."}]}


def test_html_includes_tax_when_available():
    html = generate_html_report({**_BASE, "tax_optimization": _TX})
    assert "TAX ME IF YOU CAN" in html.upper() and "Small Business Corporation" in html


def test_html_omits_tax_when_unavailable():
    assert "TAX ME IF YOU CAN" not in generate_html_report({**_BASE, "tax_optimization": {"available": False}}).upper()
    assert "TAX ME IF YOU CAN" not in generate_html_report(dict(_BASE)).upper()


def test_pdf_includes_tax_when_available():
    pdf = generate_pdf_report({**_BASE, "tax_optimization": _TX}, audience="owner")
    assert pdf[:4] == b"%PDF" and len(pdf) > 1000


def test_pdf_safe_without_tax():
    assert generate_pdf_report(dict(_BASE), audience="banker")[:4] == b"%PDF"
