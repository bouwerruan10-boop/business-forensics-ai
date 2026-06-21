"""Unit tests for the deterministic Funding-Fit / which-path recommender."""
from services.funding_fit import recommend_funding


def _fit(r, key):
    return next(o["fit"] for o in r["options"] if o["archetype"] == key)


def test_strong_clean_profile_is_application_ready():
    rep = {"annual_revenue": 8_000_000, "years_in_business": "6", "cipc_number": "2018/1/07",
           "industry_key": "manufacturing",
           "financial_figures": {"revenue": 8_000_000, "receivables": 200_000},
           "bank_signals": {"returned_debit_orders": 0},
           "lender_view": {"decline_risk": "low"},
           "normalization": {"adjusted_ebitda_low": 1_200_000}}
    r = recommend_funding(rep)
    assert r["eligibility"]["floor_met"] is True
    assert r["gate"]["status"] == "application-ready"
    assert _fit(r, "bank_term_loan") == "good"
    assert _fit(r, "working_capital_facility") == "good"


def test_thin_file_routes_to_development_funding():
    rep = {"annual_revenue": 300_000, "years_in_business": "0.5", "cipc_number": "",
           "financial_figures": {"revenue": 300_000}}
    r = recommend_funding(rep)
    assert r["eligibility"]["floor_met"] is False
    assert r["gate"]["status"] == "strengthen-first"
    assert _fit(r, "development_funding") == "good"


def test_bounced_debit_orders_trigger_strengthen_first():
    rep = {"annual_revenue": 5_000_000, "years_in_business": "4", "cipc_number": "x",
           "financial_figures": {"revenue": 5_000_000},
           "bank_signals": {"returned_debit_orders": 2}, "lender_view": {"decline_risk": "high"}}
    r = recommend_funding(rep)
    assert r["gate"]["status"] == "strengthen-first"
    assert any("bounced" in x for x in r["gate"]["reasons"])
    assert _fit(r, "bank_term_loan") == "unlikely"


def test_high_receivables_favours_invoice_discounting():
    rep = {"annual_revenue": 4_000_000, "years_in_business": "5", "cipc_number": "x",
           "financial_figures": {"revenue": 4_000_000, "receivables": 1_200_000},
           "bank_signals": {"returned_debit_orders": 0}, "lender_view": {"decline_risk": "low"}}
    assert _fit(recommend_funding(rep), "invoice_discounting") == "good"


def test_recommender_is_graceful_on_bad_input():
    for rep in (None, {}, {"financial_figures": "nope", "bank_signals": ["x"], "lender_view": 5}):
        r = recommend_funding(rep)
        assert r["available"] and "options" in r and r["gate"]["status"] in ("application-ready", "strengthen-first")
