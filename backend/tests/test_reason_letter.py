"""Adverse-action / reason letter (H3/D2): portable PDF + HTML the SME receives."""
from services.reason_letter import build_reason_letter, render_reason_letter_html
from services.report_generator import generate_reason_letter_pdf

_SCORED = {"business_name": "Acme (Pty) Ltd", "imara_score": 58, "imara_band": "B",
           "imara_components": [{"label": "Profitability", "weight": 0.30, "value": 40},
                                {"label": "Credit Readiness", "weight": 0.25, "value": 50},
                                {"label": "Risk & Compliance", "weight": 0.20, "value": 80},
                                {"label": "Operational Efficiency", "weight": 0.25, "value": 70}],
           "financial_ratios": {"net_margin": {"value": 4.2, "benchmark": 9.0}}}
_NO_SCORE = {"business_name": "NoScore Ltd", "imara_components": []}


def test_build_letter_has_reasons_rights_and_framing():
    L = build_reason_letter(_SCORED)
    assert L["available"] and L["score"] == 58 and L["band"] == "B"
    assert L["principal_reasons"] and all("factor" in r for r in L["principal_reasons"])
    assert L["how_to_contest"]                                   # POPIA s71(3) right present
    assert "does not make the credit decision" in L["basis"]    # decision-support framing
    assert "Net margin 4.2%" in " ".join(r["detail"] for r in L["principal_reasons"])  # concrete driver


def test_build_letter_noop_without_components():
    assert build_reason_letter(_NO_SCORE)["available"] is False


def test_html_renders_and_escapes_injection():
    hostile = {**_SCORED, "business_name": "<script>alert(1)</script>",
               "imara_components": [{"label": "<img src=x onerror=1>", "weight": 0.5, "value": 10},
                                    {"label": "Profitability", "weight": 0.5, "value": 90}]}
    h = render_reason_letter_html(hostile)
    assert "<script>alert(1)</script>" not in h and "&lt;script&gt;" in h
    assert "Explanation of Principal Factors" in h


def test_html_safe_without_score():
    h = render_reason_letter_html(_NO_SCORE)
    assert isinstance(h, str) and "No Imara Score factors" in h


def test_pdf_renders_and_is_robust():
    pdf = generate_reason_letter_pdf(_SCORED)
    assert pdf[:4] == b"%PDF" and len(pdf) > 800
    # hostile / no-score still produce a valid PDF
    for bad in (_NO_SCORE, {}, {"imara_components": "x", "imara_score": "y"}):
        assert generate_reason_letter_pdf(bad)[:4] == b"%PDF"
