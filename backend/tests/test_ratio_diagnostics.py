"""Deterministic ratio -> meaning -> recommendation join tests."""
from services.ratio_diagnostics import build_diagnostics


def _report():
    return {
        "financial_ratios": {
            "gross_margin": {"label": "Gross margin", "value": 18.0, "benchmark": 25.0,
                             "unit": "%", "status": "critical", "source": "rev=5m"},
            "current_ratio": {"label": "Current ratio", "value": 1.8, "benchmark": 1.5,
                              "unit": "x", "status": "good", "source": "ca/cl"},
        },
        "financial_figures": {"revenue": 5_000_000, "gross_profit": 900_000, "operating_profit": 300_000},
        "all_findings_ranked": [{"category": "Cash Flow", "title": "Gross margin below sector"}],
        "currency": "ZAR",
    }


def test_join_and_ordering():
    d = build_diagnostics(_report())
    assert d["count"] == 2
    # critical sorts before good
    first = d["diagnostics"][0]
    assert first["key"] == "gross_margin"
    assert first["gap"] == -7.0
    assert "18.0%" in first["plain_meaning"]           # evidence-backed plain language
    assert first["recommendation"]["label"]            # linked simulator action
    assert "Gross margin below sector" in first["linked_findings"]
    second = d["diagnostics"][1]
    assert second["key"] == "current_ratio"
    assert second["recommendation"] is None            # no action maps to current_ratio


def test_skips_none_values():
    rep = {"financial_ratios": {"x": {"label": "X", "value": None, "status": "good"}}}
    assert build_diagnostics(rep)["count"] == 0


def test_robust_to_garbage():
    assert build_diagnostics(None) == {"diagnostics": [], "count": 0}
    assert build_diagnostics("nope") == {"diagnostics": [], "count": 0}
    assert build_diagnostics({"financial_ratios": "bad"}) == {"diagnostics": [], "count": 0}
