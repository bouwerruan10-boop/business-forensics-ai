"""Tests for the applicability / data-sufficiency gates and their injection."""
from services.applicability import business_kind, applicability_note
from memory.shared_memory import SharedMemory
from agents import specialist_agents as SA


def _m(industry, key="general"):
    m = SharedMemory()
    m.industry = industry; m.industry_key = key
    m.currency = "ZAR"; m.country = "South Africa"
    return m


def test_business_kind_classifier():
    assert business_kind(_m("Trucking & Haulage", "logistics")) == "transport"
    assert business_kind(_m("Steel Manufacturing", "manufacturing")) == "manufacturing"
    assert business_kind(_m("Management Consulting", "services")) == "general"
    assert business_kind(_m("Retail Clothing", "retail")) == "general"


def test_classifier_robust_to_missing_fields():
    assert business_kind(type("X", (), {})()) == "general"
    assert business_kind(_m(None, None)) == "general"


def test_notes_gate_non_applicable_business():
    svc = _m("Management Consulting", "services")
    assert "DO NOT APPLY" in applicability_note(svc, "operations")
    assert "DO NOT APPLY" in applicability_note(svc, "logistics")


def test_notes_allow_applicable_business():
    assert "metrics apply" in applicability_note(_m("Trucking", "logistics"), "logistics")
    assert "DO NOT APPLY" not in applicability_note(_m("Trucking", "logistics"), "logistics")
    assert "metrics apply" in applicability_note(_m("Steel Manufacturing", "manufacturing"), "operations")


def test_sales_and_marketing_data_sufficiency():
    s = applicability_note(_m("Retail"), "sales")
    assert "not assessable from the supplied documents" in s
    assert "revenue concentration" in s        # still permits the computable ones
    mk = applicability_note(_m("Retail"), "marketing")
    assert "not assessable from the supplied documents" in mk


def _first_prompt(cls, m):
    out = []
    cls._call_claude = lambda self, p, *a, **k: (out.append(p) or "No findings.")
    cls().analyze({"general": {}}, m)
    return out[0]


def test_gates_injected_into_four_agents():
    svc = _m("Management Consulting", "services")
    svc.annual_revenue = 6_000_000; svc.headcount = 12
    assert "DO NOT APPLY" in _first_prompt(SA.OperationsAgent, svc)
    assert "DO NOT APPLY" in _first_prompt(SA.LogisticsAgent, svc)
    assert "DATA SUFFICIENCY" in _first_prompt(SA.SalesAgent, svc)
    assert "DATA SUFFICIENCY" in _first_prompt(SA.MarketingAgent, svc)
