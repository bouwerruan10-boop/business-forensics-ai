"""
Regression tests for Imara — scoring, confidence, agent JSON extraction, app boot.
All tests run with MOCK_MODE and stubbed Claude calls — NO API key required.
Run from the backend/ directory:  pytest
"""
import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")

from agents.ceo_agent import CEOAgent
from memory.shared_memory import SharedMemory, AgentFinding
from agents.specialist_agents import (
    FraudDetectionAgent, CreditReadinessAgent, ValuationAgent, ForecastAgent, ALL_AGENTS,
)


def _finding(agent, sev, title, qw=False):
    return AgentFinding(agent=agent, category="C", severity=sev, title=title, detail="d",
                        financial_impact="ZAR 1M", recommendation="r", roi_estimate="roi",
                        cost_of_inaction="coi", benchmark_reference="b", quick_win=qw)


def _ceo():
    return CEOAgent.__new__(CEOAgent)


def _full_memory():
    m = SharedMemory()
    m.business_name = "Test (Pty) Ltd"; m.industry_key = "retail"; m.currency = "ZAR"
    m.annual_revenue = 8_000_000
    m.findings = [
        _finding("Financial Forensics Agent", "high", "Margin low"),
        _finding("Operations Agent", "high", "Stock slow"),
        _finding("Credit Readiness Agent", "high", "DSCR low"),
    ]
    m.credit_score = 60; m.credit_grade = "C"
    m.fraud_risk_level = "medium"; m.fraud_risk_score = 30
    m.valuation_mid = 5_000_000
    m.market_search_performed = True; m.market_visibility_score = 60
    m.sa_tax_performed = True; m.sa_tax_risk_score = 25
    m.sa_legal_performed = True; m.sa_legal_risk_score = 25
    return m


# ── Imara Score ───────────────────────────────────────────────────────────

def test_imara_full_profile_is_high_confidence():
    m = _full_memory(); ceo = _ceo()
    ceo._score_business(m); ceo._calculate_imara_score(m)
    assert 0 <= m.imara_score <= 100
    assert m.imara_band in ("A", "B", "C", "D", "E")
    assert m.imara_confidence == "high"
    assert m.imara_completeness == 100
    assert len(m.imara_components) == 8
    assert abs(sum(c["weight"] for c in m.imara_components) - 1.0) < 0.001
    assert m.imara_color.startswith("#")


def test_imara_thin_profile_flags_lower_confidence():
    m = SharedMemory(); m.industry_key = "retail"; m.currency = "ZAR"
    m.findings = [_finding("Financial Forensics Agent", "high", "x"),
                  _finding("Operations Agent", "medium", "y")]
    ceo = _ceo(); ceo._score_business(m); ceo._calculate_imara_score(m)
    assert m.imara_confidence in ("low", "medium")
    assert m.imara_completeness < 100
    assert abs(sum(c["weight"] for c in m.imara_components) - 1.0) < 0.001


def test_imara_empty_uses_fallback():
    m = SharedMemory(); ceo = _ceo()
    ceo._score_business(m); ceo._calculate_imara_score(m)
    assert 0 <= m.imara_score <= 100
    assert m.imara_band in ("A", "B", "C", "D", "E")
    assert m.imara_confidence == "low"


def test_score_business_caps_volume():
    # 40 critical findings in one category must not drive the sub-score below the cap floor.
    m = SharedMemory()
    m.findings = [_finding("Financial Forensics Agent", "critical", f"f{i}") for i in range(40)]
    ceo = _ceo(); ceo._score_business(m)
    assert m.profitability_score >= 40  # capped penalty (=60) -> >= 100-60


# ── Reconstructed agents: structured JSON extraction ──────────────────────

def _stub(agent_cls, raw):
    a = agent_cls()
    a._call_claude = lambda *x, **k: raw
    a._parse_findings = lambda raw, mem: []
    a._build_benchmark_block = lambda mem: ""  # isolate from the data file
    return a


def test_fraud_agent_extracts_json():
    m = SharedMemory()
    _stub(FraudDetectionAgent,
          '{"fraud_risk_level":"high","fraud_risk_score":70,"fraud_indicators":["a","b"]}').analyze({}, m)
    assert m.fraud_risk_level == "high" and m.fraud_risk_score == 70 and len(m.fraud_indicators) == 2


def test_credit_agent_extracts_json():
    m = SharedMemory()
    _stub(CreditReadinessAgent,
          '{"credit_score":72,"credit_grade":"B","credit_barriers":[],"credit_strengths":[],"credit_products":[]}').analyze({}, m)
    assert m.credit_score == 72 and m.credit_grade == "B"


def test_valuation_agent_extracts_json():
    m = SharedMemory(); m.currency = "ZAR"; m.annual_revenue = 8_000_000
    _stub(ValuationAgent,
          '{"valuation_low":4e6,"valuation_mid":5.8e6,"valuation_high":7.5e6,"valuation_method":"x","valuation_ebitda_multiple":4.2,"valuation_normalised_ebitda":1.3e6}').analyze({}, m)
    assert m.valuation_mid == 5_800_000 and m.valuation_ebitda_multiple == 4.2


def test_forecast_agent_extracts_json():
    m = SharedMemory(); m.currency = "ZAR"
    _stub(ForecastAgent,
          '{"forecast_base_12m":9e6,"forecast_bull_12m":1e7,"forecast_bear_12m":8e6,"forecast_assumptions":[],"forecast_monthly":[]}').analyze({}, m)
    assert m.forecast_base_12m == 9_000_000


def test_fraud_agent_fallback_without_json():
    m = SharedMemory()
    a = FraudDetectionAgent()
    a._build_benchmark_block = lambda mem: ""
    a._call_claude = lambda *x, **k: "no json here"
    a._parse_findings = lambda raw, mem: [_finding("Fraud & Anomaly Detection Agent", "high", "Ghost employees")]
    a.analyze({}, m)
    assert m.fraud_risk_level == "high" and m.fraud_risk_score > 0 and m.fraud_indicators


# ── App boot ──────────────────────────────────────────────────────────────

def test_all_agents_registered():
    assert len(ALL_AGENTS) == 15
    for A in ALL_AGENTS:
        assert isinstance(A.name, str) and A.name


def test_app_imports_and_has_routes():
    from main import app
    assert len(app.routes) > 5
