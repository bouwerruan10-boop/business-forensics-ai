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


# ── Deterministic financial ratios ────────────────────────────────────────
from services.financial_ratios import (
    parse_amount, extract_financials, compute_ratios, fundamentals_score,
)

_STATEMENT = """Revenue 8,000,000
Cost of sales 5,344,000
Gross profit 2,656,000
Operating profit 656,000
Net profit 448,000
Current assets 2,400,000
Current liabilities 1,600,000
Inventory 900,000
Trade receivables 1,200,000
Trade payables 700,000
Total borrowings 1,800,000
Equity 2,000,000
Finance costs 180,000"""


def test_parse_amount_formats():
    assert parse_amount("R 1 200 000") == 1_200_000
    assert parse_amount("1.2m") == 1_200_000
    assert parse_amount("8,000,000") == 8_000_000
    assert parse_amount("(500)") == -500
    assert parse_amount("not a number") is None


def test_extract_financials():
    f = extract_financials(_STATEMENT)
    assert f["revenue"] == 8_000_000
    assert f["gross_profit"] == 2_656_000
    assert f["current_liabilities"] == 1_600_000
    assert f["equity"] == 2_000_000


def test_compute_ratios_values_and_source():
    r = compute_ratios(extract_financials(_STATEMENT), "retail_general", 8_000_000)
    # gross margin 2.656M / 8M = 33.2%
    assert abs(r["gross_margin"]["value"] - 33.2) < 0.2
    # current ratio 2.4M / 1.6M = 1.5x
    assert abs(r["current_ratio"]["value"] - 1.5) < 0.01
    # every ratio is traceable to source figures
    for v in r.values():
        assert v["source"] and "=" in v["source"]
    # debtor days are critical for retail (benchmark 12)
    assert r["debtor_days"]["status"] == "critical"


def test_fundamentals_score_range():
    r = compute_ratios(extract_financials(_STATEMENT), "retail_general", 8_000_000)
    fs = fundamentals_score(r, "retail_general")
    assert fs["available"] and 0 <= fs["score"] <= 100 and fs["components_used"] >= 4


def test_fundamentals_score_empty():
    fs = fundamentals_score({}, "general")
    assert fs["available"] is False and fs["score"] is None


def test_imara_profitability_anchored_on_fundamentals():
    m = _full_memory()
    m.financial_fundamentals_score = 30  # weak fundamentals should pull profitability down
    ceo = _ceo(); ceo._score_business(m)
    base_prof = m.profitability_score
    ceo._calculate_imara_score(m)
    prof_comp = next(c for c in m.imara_components if c["label"] == "Profitability")
    # blended 0.6*30 + 0.4*base; must differ from the raw sub-score when they diverge
    expected = round(0.6 * 30 + 0.4 * base_prof)
    assert prof_comp["value"] == expected


# ── Parser → ratios integration (regression for summary-CSV extraction) ────
from services.file_parser import parse_file

_SUMMARY_CSV = (
    b"Acme (Pty) Ltd Financial Statements,\n"
    b"INCOME STATEMENT,\n"
    b"Revenue,8000000\n"
    b"Cost of sales,5344000\n"
    b"Gross profit,2656000\n"
    b"Operating profit,656000\n"
    b"Net profit,448000\n"
    b"BALANCE SHEET,\n"
    b"Current assets,2400000\n"
    b"Current liabilities,1600000\n"
    b"Inventory,900000\n"
    b"Trade receivables,1200000\n"
    b"Equity,2000000\n"
)


def test_parser_emits_clean_text():
    parsed = parse_file("statement.csv", _SUMMARY_CSV)
    text = parsed.get("text", "")
    assert text, "parser must expose a top-level 'text' key"
    assert "Revenue: 8000000" in text  # label: value, not a dict repr
    assert "col_1" not in text         # no opaque column noise


def test_ratios_extract_from_summary_csv():
    # The exact failure mode from the live test: summary-statement CSV.
    parsed = parse_file("statement.csv", _SUMMARY_CSV)
    text = parsed.get("text", "") or str(parsed)
    figs = extract_financials(text)
    assert figs.get("revenue") == 8_000_000
    assert figs.get("gross_profit") == 2_656_000
    ratios = compute_ratios(figs, "retail_general", 8_000_000)
    assert "gross_margin" in ratios and abs(ratios["gross_margin"]["value"] - 33.2) < 0.5
    assert "current_ratio" in ratios
    fs = fundamentals_score(ratios, "retail_general")
    assert fs["available"] and fs["score"] is not None


# ── Phase 1: faithfulness verification ─────────────────────────────────────
from services.faithfulness import verify_findings

class _Fnd:
    def __init__(self, title, detail="", benchmark_reference=""):
        self.title = title; self.detail = detail; self.benchmark_reference = benchmark_reference
        self.verification = ""; self.verification_note = ""

_RATIOS = {
    "gross_margin": {"value": 33.2, "label": "Gross Margin"},
    "current_ratio": {"value": 1.5, "label": "Current Ratio"},
    "debtor_days": {"value": 55.0, "label": "Debtor Days"},
}

def test_faithfulness_flags_conflict():
    # The exact live-test hallucination: claims 21.3% when computed is 33.2%.
    f = _Fnd("Gross Margin ~21.3% vs Industry Median 37.8%", "R1.32M erosion")
    summary = verify_findings([f], _RATIOS)
    assert f.verification == "conflict"
    assert "33.2" in f.verification_note
    assert summary["conflicts"] == 1 and summary["checked"] == 1

def test_faithfulness_confirms_match():
    f = _Fnd("Current Ratio healthy at 1.5x")
    verify_findings([f], _RATIOS)
    assert f.verification == "confirmed"

def test_faithfulness_ignores_unverifiable():
    f = _Fnd("Staff turnover ~35% costs R956k")  # no computed metric for this
    verify_findings([f], _RATIOS)
    assert f.verification == ""

def test_faithfulness_no_ratios_is_safe():
    f = _Fnd("Gross margin 21.3%")
    summary = verify_findings([f], {})
    assert f.verification == "" and summary["checked"] == 0


# ── Phase 0: eval harness (deterministic, runs in CI) ──────────────────────
from evals.grader import load_cases, grade_deterministic, deterministic_report

def test_golden_cases_exist():
    cases = load_cases()
    assert len(cases) >= 2

def test_deterministic_eval_passes_on_golden_set():
    # Each golden case's computed ratios must match its known-correct expectations.
    rep = deterministic_report()
    for r in rep["results"]:
        assert r["passed"] == r["total"], (r["name"], [c for c in r["checks"] if not c["pass"]])
    assert rep["overall_score"] == 100


# ── Phase 2: parallel specialist waves ─────────────────────────────────────
from agents.parallel import run_agent_waves
from memory.shared_memory import SharedMemory as _SM, AgentFinding as _AF

def _fake_agent(agent_name, fail=False):
    def analyze(self, business_data, memory):
        if fail:
            raise RuntimeError("boom")
        return [_AF(agent=agent_name, category="C", severity="low", title=agent_name + " finding",
                    detail="d", financial_impact="R1", recommendation="r", roi_estimate="x",
                    cost_of_inaction="y", benchmark_reference="b", quick_win=False)]
    return type("A_" + agent_name.replace(" ", "_"), (), {"name": agent_name, "analyze": analyze})

def test_parallel_waves_run_all_and_merge_in_declared_order():
    mem = _SM()
    classes = [_fake_agent("Financial Forensics Agent"), _fake_agent("Strategy Agent"),
               _fake_agent("Accounting Agent"), _fake_agent("Valuation Agent")]
    run_agent_waves(classes, {"financial": {}}, mem)
    timed = [t["agent"] for t in mem.agent_timings]
    # Wave 1 (base) merged before Wave 2 (synthesis), each in declared order.
    assert timed == ["Financial Forensics Agent", "Accounting Agent", "Strategy Agent", "Valuation Agent"]
    assert len(mem.findings) == 4

def test_parallel_wave_isolates_a_failing_agent():
    mem = _SM()
    run_agent_waves([_fake_agent("Operations Agent", fail=True), _fake_agent("Sales Agent")], {}, mem)
    assert len(mem.findings) == 1                 # only the healthy agent contributed
    assert len(mem.agent_timings) == 2            # both still timed/observed


# ── Phase 2b–2d: parallel independent tail (market + SA tax + SA legal) ─────
from agents.parallel import run_independent_agents

def test_independent_agents_merge_in_order_isolate_failure_and_set_fields():
    mem = _SM()
    def mk(title, **fields):
        class _A:
            def analyze(self, bd, m):
                for k, v in fields.items():
                    setattr(m, k, v)
                return [_AF(agent=title, category="C", severity="low", title=title,
                            detail="d", financial_impact="R1", recommendation="r", roi_estimate="x",
                            cost_of_inaction="y", benchmark_reference="b", quick_win=False)]
        return _A()
    class Boom:
        def analyze(self, bd, m):
            raise RuntimeError("x")
    items = [
        (mk("market", market_visibility_score=55), "Market Intelligence Agent", ""),
        (Boom(), "SA Tax Compliance Agent", ""),           # fails -> isolated
        (mk("legal", sa_legal_risk_score=30, sa_legal_performed=True), "SA Corporate Law & BBBEE Agent", ""),
    ]
    run_independent_agents(items, {}, mem)
    titles = [f.title for f in mem.findings]
    assert titles == ["market", "legal"]                   # declared order, failure skipped
    assert mem.market_visibility_score == 55
    assert mem.sa_legal_risk_score == 30 and mem.sa_legal_performed


# ── Reliability: orphaned-job cleanup survives a restart ───────────────────
def test_mark_interrupted_analyses(tmp_path, monkeypatch):
    import services.database as db
    monkeypatch.setattr(db, "_DB_PATH", tmp_path / "t.db")
    db.init_db()
    db.create_analysis("11111111-1111-1111-1111-111111111111", {"company_name": "X"}, 1)
    assert db.get_analysis("11111111-1111-1111-1111-111111111111")["status"] == "processing"
    # a restart leaves it orphaned -> flagged as error
    assert db.mark_interrupted_analyses() == 1
    assert db.get_analysis("11111111-1111-1111-1111-111111111111")["status"] == "error"
    # completed rows must never be touched
    db.create_analysis("22222222-2222-2222-2222-222222222222", {"company_name": "Y"}, 1)
    db.save_report("22222222-2222-2222-2222-222222222222", {"ok": True})
    assert db.mark_interrupted_analyses() == 0


# ── Security: opt-in admin gate ────────────────────────────────────────────
def test_admin_gate(monkeypatch):
    import main, pytest as _pt
    from fastapi import HTTPException
    class _Req:
        def __init__(self, headers): self.headers = headers
    # disabled when no key configured -> passes through
    monkeypatch.setattr(main, "ADMIN_API_KEY", "")
    assert main.verify_admin_key(_Req({})) is None
    # enabled: missing or wrong key -> 401
    monkeypatch.setattr(main, "ADMIN_API_KEY", "s3cret")
    with _pt.raises(HTTPException):
        main.verify_admin_key(_Req({}))
    with _pt.raises(HTTPException):
        main.verify_admin_key(_Req({"X-Admin-Key": "nope"}))
    # correct key -> passes
    assert main.verify_admin_key(_Req({"X-Admin-Key": "s3cret"})) is None


# ── Security: expiring/revocable share tokens ──────────────────────────────
def test_share_tokens(tmp_path, monkeypatch):
    import services.database as db
    from datetime import datetime, timezone, timedelta
    monkeypatch.setattr(db, "_DB_PATH", tmp_path / "t.db")
    db.init_db()
    aid = "33333333-3333-3333-3333-333333333333"
    db.create_analysis(aid, {"company_name": "Z"}, 1)
    # valid token resolves to the analysis
    tok = db.create_share(aid)
    assert db.resolve_share(tok) == aid
    # revoked token -> None
    assert db.revoke_share(tok) is True
    assert db.resolve_share(tok) is None
    # expired token -> None
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert db.resolve_share(db.create_share(aid, past)) is None
    # future expiry -> valid
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    assert db.resolve_share(db.create_share(aid, future)) == aid
    # unknown token -> None
    assert db.resolve_share("does-not-exist") is None


# ── Front 4: financial extraction validation ───────────────────────────────
def test_validate_financials():
    from services.financial_ratios import validate_financials, KNOWN_FIGURE_FIELDS
    assert "revenue" in KNOWN_FIGURE_FIELDS and "equity" in KNOWN_FIGURE_FIELDS
    # consistent income statement -> ok, with at least one reconciliation check run
    ok = validate_financials({"revenue": 1000, "cogs": 600, "gross_profit": 400, "operating_profit": 250})
    assert ok["ok"] is True and ok["checks"] >= 1
    # gross profit doesn't reconcile to revenue - cogs -> flagged
    assert validate_financials({"revenue": 1000, "cogs": 600, "gross_profit": 250})["ok"] is False
    # operating profit exceeds gross profit -> flagged
    assert validate_financials({"revenue": 1000, "cogs": 600, "gross_profit": 400, "operating_profit": 500})["ok"] is False
    # negative balance-sheet item -> flagged
    assert validate_financials({"revenue": 100, "equity": -5})["ok"] is False


# ── Action Simulator (deterministic prescriptive engine) ───────────────────
def _sim_report():
    from services.financial_ratios import compute_ratios, fundamentals_score
    figs = {"revenue": 8000000, "cogs": 6400000, "gross_profit": 1600000,
            "operating_profit": 200000, "net_profit": 50000, "receivables": 1200000,
            "inventory": 900000, "current_assets": 2400000, "current_liabilities": 1600000,
            "payables": 700000, "total_debt": 1800000, "equity": 2000000, "interest": 180000}
    ratios = compute_ratios(figs, "retail_general", 8000000)
    fund = fundamentals_score(ratios, "retail_general").get("score") or 0
    comps = [{"label": "Profitability", "value": 40, "weight": 0.25},
             {"label": "Credit Readiness", "value": 55, "weight": 0.20},
             {"label": "Risk & Compliance", "value": 60, "weight": 0.15}]
    composite = round((40*0.25 + 55*0.20 + 60*0.15) / 0.60)
    return {"financial_figures": figs, "financial_ratios": ratios, "industry_key": "retail_general",
            "annual_revenue": 8000000, "currency": "ZAR", "financial_fundamentals_score": fund,
            "imara_score": composite, "imara_components": comps}

def test_simulation_derive_actions_grounded():
    from services.simulation import derive_actions
    ids = {a["id"] for a in derive_actions(_sim_report())}
    # low gross margin + high debtor/inventory days + low operating margin -> all gap actions present
    assert {"gross_margin", "debtor_days", "inventory_days", "opex", "revenue_growth", "price"} <= ids

def test_simulation_no_actions_is_no_change():
    from services.simulation import apply_actions
    r = apply_actions(_sim_report(), [], "expected")
    assert r["net_profit_delta"] == 0
    assert r["imara_score_delta"] == 0
    assert r["projected"] == r["baseline"]

def test_simulation_action_improves_outcome():
    from services.simulation import apply_actions
    rep = _sim_report()
    gm = apply_actions(rep, [{"id": "gross_margin", "intensity": 1.0}], "expected")
    assert gm["projected"]["gross_profit"] > gm["baseline"]["gross_profit"]
    assert gm["net_profit_delta"] > 0
    assert gm["projected"]["fundamentals_score"] >= gm["baseline"]["fundamentals_score"]
    assert gm["imara_score_delta"] >= 0
    # collecting faster frees cash
    dd = apply_actions(rep, [{"id": "debtor_days", "intensity": 1.0}], "expected")
    assert dd["cash_released"] > 0

def test_simulation_scenarios_scale_monotonically():
    from services.simulation import apply_actions
    rep = _sim_report(); sel = [{"id": "gross_margin", "intensity": 1.0}]
    opt = apply_actions(rep, sel, "optimistic")["net_profit_delta"]
    exp = apply_actions(rep, sel, "expected")["net_profit_delta"]
    pes = apply_actions(rep, sel, "pessimistic")["net_profit_delta"]
    assert opt > exp > pes > 0


# ── Action Simulator v2: tax, sensitivity ranking, Monte Carlo ─────────────
def test_simulation_tax_reduces_net_gain():
    from services.simulation import apply_actions
    r = apply_actions(_sim_report(), [{"id": "gross_margin", "intensity": 1.0}], "optimistic")
    # incremental net should be positive but less than the gross operating gain (tax applied)
    op_gain = r["projected"]["operating_profit"] - r["baseline"]["operating_profit"]
    assert 0 < r["net_profit_delta"] < op_gain  # ~73% of the operating gain

def test_simulation_rank_levers_sorted():
    from services.simulation import rank_levers
    levers = rank_levers(_sim_report(), "expected")
    assert len(levers) >= 4
    scores = [l["score_impact"] for l in levers]
    assert scores == sorted(scores, reverse=True)  # ranked, biggest first

def test_simulation_monte_carlo_deterministic_and_bounded():
    from services.simulation import monte_carlo
    rep = _sim_report(); sel = [{"id": "gross_margin", "intensity": 1.0}]
    a = monte_carlo(rep, sel, n=400, seed=7)
    b = monte_carlo(rep, sel, n=400, seed=7)
    assert a == b                                   # seeded -> reproducible
    sc = a["imara_score"]
    assert sc["p10"] <= sc["p50"] <= sc["p90"]      # ordered percentiles
    assert 0.0 <= a["prob_reach_next_band"] <= 1.0  # valid probability
    assert a["net_profit_delta"]["p50"] >= 0        # a beneficial action centres positive

def test_simulation_plausibility_no_absurd_state():
    from services.simulation import apply_actions
    # stack everything at full optimism -> must stay plausible (positive revenue, sane margin)
    rep = _sim_report()
    sel = [{"id": i, "intensity": 1.0} for i in ("gross_margin", "opex", "revenue_growth", "price")]
    r = apply_actions(rep, sel, "optimistic")
    assert r["projected"]["revenue"] > 0
    assert -5 <= (r["projected"]["gross_margin"] or 0) <= 100


# ── Future-proofing seams (operator-run today; ready for the pivot) ────────
def test_principal_defaults_to_operator():
    from auth import get_principal, Principal
    class _Req:
        headers = {}
    p = get_principal(_Req())
    assert isinstance(p, Principal) and p.id == "operator" and p.kind == "operator"

def test_score_contract_is_versioned_and_stable():
    from services.score_contract import score_contract, SCORE_SCHEMA_VERSION
    rep = {"imara_score": 47, "imara_band": "D", "imara_label": "At Risk", "business_name": "X",
           "currency": "ZAR", "imara_confidence": "high", "imara_completeness": 100,
           "imara_components": [{"label": "Profitability", "value": 40, "weight": 0.25}]}
    c = score_contract(rep, "abc")
    assert c["schema_version"] == SCORE_SCHEMA_VERSION
    assert c["analysis_id"] == "abc" and c["imara_score"] == 47 and c["band"] == "D"
    assert isinstance(c["components"], list) and "generated_at" in c

def test_db_owner_isolation_seam(tmp_path, monkeypatch):
    import services.database as db
    monkeypatch.setattr(db, "_DB_PATH", tmp_path / "t.db"); db.init_db()
    db.create_analysis("a1", {"company_name": "X"}, 1, owner="operator")
    db.create_analysis("a2", {"company_name": "Y"}, 1, owner="tenantA")
    assert [r["id"] for r in db.list_analyses(owner="operator")] == ["a1"]
    assert db.get_analysis("a2", owner="operator") is None          # isolation
    assert db.get_analysis("a2", owner="tenantA")["id"] == "a2"
    assert sorted(r["id"] for r in db.list_analyses()) == ["a1", "a2"]  # no filter -> all (operator mode)

def test_public_api_dormant_by_default(monkeypatch):
    import main
    import pytest as _pt
    from fastapi import HTTPException
    monkeypatch.setattr(main, "PUBLIC_API", False)
    with _pt.raises(HTTPException):
        main.public_score("anything")  # gated off until the pivot


# ── SA Compliance RAG grounding ────────────────────────────────────────────
def test_sa_knowledge_corpus_well_formed():
    from services.sa_knowledge import KNOWLEDGE_BASE
    assert len(KNOWLEDGE_BASE) >= 15
    for e in KNOWLEDGE_BASE:
        assert e["domain"] in ("tax", "legal")
        assert e["citation"] and any(ch.isdigit() for ch in e["citation"])  # Act number present
        assert e["as_of"] and e["keywords"] and e["text"]
    ids = [e["id"] for e in KNOWLEDGE_BASE]
    assert len(ids) == len(set(ids))  # unique ids


def test_sa_knowledge_retrieval_is_relevant_and_deterministic():
    from services.sa_knowledge import retrieve
    top = retrieve("must I register for VAT given turnover threshold", domain="tax", k=3)
    assert top[0]["id"] == "vat_threshold"
    top2 = retrieve("exempt micro enterprise BBBEE level", domain="legal", k=3)
    assert top2[0]["id"] == "bbbee"
    # domain filtering: a legal query never returns tax-domain entries
    assert all(e["domain"] == "legal" for e in retrieve("director duties", domain="legal", k=5))
    # deterministic
    assert [e["id"] for e in retrieve("vat", "tax", 4)] == [e["id"] for e in retrieve("vat", "tax", 4)]


def test_sa_grounding_block_carries_citations():
    from services.sa_knowledge import retrieve_grounding
    class M:
        industry_key="retail"; entity_type="Pty Ltd"; primary_concern="vat"; years_in_business="5"
        vat_registered="yes"; headcount=10; bbbee_level="Level 4"
    g_tax = retrieve_grounding(M(), "tax")
    g_legal = retrieve_grounding(M(), "legal")
    assert "AUTHORITATIVE SA PROVISIONS" in g_tax and "VAT Act 89 of 1991" in g_tax
    assert "Companies Act 71 of 2008" in g_legal


def test_sa_agents_inject_grounding_into_prompt():
    from agents.specialist_agents import SATaxAgent, SALegalAgent
    from memory.shared_memory import SharedMemory
    m = SharedMemory(); m.business_name="T"; m.industry="retail"; m.vat_registered="yes"
    m.entity_type="Pty Ltd"; m.annual_revenue=8_000_000; m.headcount=5; m.currency="R"
    for Agent, cite in [(SATaxAgent, "VAT Act 89 of 1991"), (SALegalAgent, "Companies Act 71 of 2008")]:
        a = Agent(); cap = {}
        def stub(prompt, *args, _c=cap, **kw):
            _c.setdefault("p", prompt); return "[]"
        a._call_claude = stub
        a.analyze({}, m)
        assert "AUTHORITATIVE SA PROVISIONS" in cap["p"]
        assert cite in cap["p"]


# ── Build 2: eval quality framework ────────────────────────────────────────
def _fake_report():
    return {"department_findings": {
        "Financial": [
            {"agent": "FinancialAgent", "severity": "high", "title": "Cash drain",
             "detail": "Operating cash flow negative", "financial_impact": "R 450 000 annual drain",
             "recommendation": "Renegotiate supplier terms to 60 days", "benchmark_reference": "Retail median DSO 45d"},
        ],
        "SA Tax": [
            {"agent": "SA Tax Compliance Agent", "severity": "critical", "title": "VAT exposure",
             "detail": "Turnover exceeds R1m but not VAT registered, breaching VAT Act 89 of 1991 s23",
             "financial_impact": "R 120 000 penalty risk", "recommendation": "Register for VAT within 21 days",
             "benchmark_reference": "VAT Act 89 of 1991, s23"},
        ],
    }}


def test_grade_structure_scores_contract_compliance():
    from evals.grader import grade_structure
    r = grade_structure(_fake_report())
    assert r["findings"] == 2
    assert r["pct"]["quantified_zar"] == 100      # both cite R-amounts
    assert r["pct"]["has_recommendation"] == 100
    assert r["pct"]["valid_severity"] == 100
    assert 0 <= r["score"] <= 100


def test_grade_sa_citation_detects_grounded_citations():
    from evals.grader import grade_sa_citation
    r = grade_sa_citation(_fake_report())
    assert r["sa_findings"] == 1
    assert r["cited"] == 1 and r["score"] == 100   # SA finding cites "Act 89 of 1991, s23"


def test_llm_judge_is_injectable_and_aggregates():
    from evals.grader import grade_findings_with_judge, build_judge_prompt
    # stub judge returns fixed JSON — tests aggregation without an API
    def judge(prompt):
        assert "specificity" in prompt and "Return ONLY JSON" in prompt
        return '{"specificity":4,"actionability":5,"grounding":4,"severity_fit":3,"comment":"ok"}'
    out = grade_findings_with_judge(_fake_report(), judge)
    assert out["judged"] == 2
    assert out["by_criterion"]["actionability"] == 5.0
    assert out["overall_1to5"] == 4.0   # mean of 4,5,4,3


def test_llm_judge_survives_bad_output():
    from evals.grader import grade_findings_with_judge
    out = grade_findings_with_judge(_fake_report(), lambda p: "not json at all")
    assert out["judged"] == 0 and out["overall_1to5"] is None


# ── Build 3: observability/tracing seam ────────────────────────────────────
def test_tracing_cost_model_and_env_override(monkeypatch):
    from services.tracing import cost_usd
    assert cost_usd("claude-sonnet-4-6", 1_000_000, 0) == 3.0
    assert cost_usd("claude-haiku-4-5-20251001", 0, 1_000_000) == 5.0
    monkeypatch.setenv("IMARA_PRICE_CLAUDE_SONNET_4_6", "2.5,12.0")
    assert cost_usd("claude-sonnet-4-6", 1_000_000, 0) == 2.5


def test_tracing_ledger_aggregates_by_model():
    from services.tracing import UsageLedger
    led = UsageLedger()
    led.record("FinancialAgent", "claude-sonnet-4-6", 2000, 800, 1200)
    led.record("FinancialAgent", "claude-haiku-4-5-20251001", 1500, 400, 600)
    s = led.summary()
    assert s["calls"] == 2 and s["input_tokens"] == 3500 and s["output_tokens"] == 1200
    assert set(s["by_model"]) == {"claude-sonnet-4-6", "claude-haiku-4-5-20251001"}
    assert s["est_cost_usd"] > 0


def test_tracing_record_call_is_safe_without_ledger():
    # No active ledger -> record_call must be a no-op, never raise.
    import importlib, services.tracing as tr
    importlib.reload(tr)
    assert tr.current_ledger() is None
    tr.record_call("x", "claude-sonnet-4-6", 10, 10, 5)  # should not raise


def test_tracing_enabled_reflects_env(monkeypatch):
    import services.tracing as tr
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("TRACING_ENABLED", raising=False)
    assert tr.tracing_enabled() is False
    monkeypatch.setenv("TRACING_ENABLED", "1")
    assert tr.tracing_enabled() is True


def test_tracing_ledger_propagates_into_parallel_workers():
    import types
    import agents.base_agent as ba
    from services.tracing import new_ledger
    from agents.parallel import run_agent_waves
    from agents.specialist_agents import FinancialAgent, AccountingAgent
    from memory.shared_memory import SharedMemory

    class _U: input_tokens = 1000; output_tokens = 300
    class _R:
        usage = _U()
        content = [types.SimpleNamespace(text="[]")]
    ba.client = types.SimpleNamespace(messages=types.SimpleNamespace(create=lambda **k: _R()))

    m = SharedMemory(business_name="T", industry_key="retail", annual_revenue=5_000_000, currency="R")
    ledger = new_ledger()
    run_agent_waves([FinancialAgent, AccountingAgent], {}, m, None)
    s = ledger.summary()
    assert s["calls"] >= 2 and s["input_tokens"] >= 2000  # recorded from worker threads


def test_usage_summary_passes_through_llm_usage():
    from services.score_contract import usage_summary
    rep = {"agent_timings": [], "llm_usage": {"calls": 5, "est_cost_usd": 0.12}}
    out = usage_summary(rep)
    assert out["llm_usage"]["calls"] == 5 and out["llm_usage"]["est_cost_usd"] == 0.12


# ── Build 4: deterministic finding self-critique ───────────────────────────
def test_finding_critique_strong_vs_weak():
    from services.finding_quality import critique_finding
    strong = {"severity": "medium", "financial_impact": "R 450 000 annual drain",
              "detail": "Operating cash flow negative for 4 months", "recommendation": "Renegotiate supplier terms to net-60 days",
              "benchmark_reference": "Retail median DSO 45 days", "cost_of_inaction": "R 1.2m erosion over 3 years"}
    flags, q = critique_finding(strong)
    assert flags == [] and q == "strong"

    weak = {"severity": "critical", "financial_impact": "Unquantified", "detail": "vague",
            "recommendation": "Review", "benchmark_reference": "see analysis above", "cost_of_inaction": ""}
    flags, q = critique_finding(weak)
    assert "unquantified" in flags and "severity_impact_mismatch" in flags and q == "weak"


def test_finding_critique_severity_mismatch_only_when_unquantified():
    from services.finding_quality import critique_finding
    # critical but well-quantified -> no mismatch flag
    f = {"severity": "critical", "financial_impact": "R 2.0m SARS penalty exposure",
         "detail": "VAT not registered above R1m threshold", "recommendation": "Register for VAT within 21 business days",
         "benchmark_reference": "VAT Act 89 of 1991 s23", "cost_of_inaction": "Penalties compound monthly"}
    flags, q = critique_finding(f)
    assert "severity_impact_mismatch" not in flags and q == "strong"


def test_critique_report_mutates_both_views_and_dedupes_summary():
    from services.finding_quality import critique_report
    strong = {"severity": "low", "financial_impact": "R 10 000", "detail": "d",
              "recommendation": "Do the specific thing now", "benchmark_reference": "Sector 12%", "cost_of_inaction": "loss"}
    weak = {"severity": "high", "financial_impact": "Unquantified", "detail": "d",
            "recommendation": "Look", "benchmark_reference": "", "cost_of_inaction": ""}
    rep = {"department_findings": {"Fin": [strong]}, "all_findings_ranked": [strong, weak]}
    summ = critique_report(rep)
    assert summ["total"] == 2 and summ["strong"] == 1 and summ["weak"] == 1   # strong counted once
    assert strong["quality"] == "strong" and weak["quality"] == "weak"        # both views tagged
    assert summ["strong_pct"] == 50
    # idempotent
    summ2 = critique_report(rep)
    assert summ2 == summ and strong["quality_flags"] == []


# ── Build 5: simulator bundle optimiser ────────────────────────────────────
def _opt_report():
    return {
        "currency": "ZAR", "industry_key": "retail", "imara_score": 44,
        "financial_fundamentals_score": 40,
        "imara_components": [
            {"label": "Profitability", "weight": 0.25, "value": 38},
            {"label": "Liquidity", "weight": 0.15, "value": 50},
            {"label": "Leverage", "weight": 0.15, "value": 45},
            {"label": "Compliance", "weight": 0.15, "value": 40},
            {"label": "Market", "weight": 0.10, "value": 55},
            {"label": "Governance", "weight": 0.20, "value": 42},
        ],
        "financial_figures": {
            "revenue": 12_000_000, "cogs": 8_700_000, "opex": 3_000_000, "interest": 180_000,
            "receivables": 2_300_000, "inventory": 1_900_000,
            "current_assets": 4_600_000, "current_liabilities": 3_100_000,
            "payables": 1_400_000, "total_debt": 2_200_000, "equity": 1_800_000, "net_profit": 120_000,
        },
        "financial_ratios": {
            "gross_margin": {"value": 27.5, "benchmark": 34.0},
            "operating_margin": {"value": 2.5, "benchmark": 7.0},
            "debtor_days": {"value": 70, "benchmark": 45},
            "inventory_days": {"value": 80, "benchmark": 60},
        },
    }


def test_optimizer_matches_bruteforce_optimum():
    from itertools import combinations
    from services.simulation import optimize_actions, derive_actions, apply_actions
    rep = _opt_report()
    opt = optimize_actions(rep, scenario="expected", max_actions=3, objective="imara")
    ids = [a["id"] for a in derive_actions(rep)]
    best = -1e9
    for k in range(1, 4):
        for combo in combinations(ids, k):
            d = apply_actions(rep, [{"id": i, "intensity": 1.0} for i in combo], "expected")["imara_score_delta"]
            best = max(best, d)
    assert opt["best_bundle"]["objective_value"] == best  # provably optimal


def test_optimizer_respects_budget_and_curve_is_monotonic():
    from services.simulation import optimize_actions
    rep = _opt_report()
    opt = optimize_actions(rep, scenario="expected", max_actions=2, objective="imara")
    assert opt["best_bundle"]["size"] <= 2                       # budget respected
    vals = [c["objective_value"] for c in opt["marginal_curve"]]
    assert vals == sorted(vals)                                   # more budget never hurts
    assert opt["best_bundle"]["ids"]                              # non-empty


def test_optimizer_tie_prefers_smaller_bundle():
    from services.simulation import optimize_actions
    rep = _opt_report()
    opt = optimize_actions(rep, scenario="expected", max_actions=4, objective="imara")
    top = opt["best_bundle"]
    # No strictly-better-or-equal smaller bundle should be ranked below the winner.
    for r in opt["top_bundles"]:
        if r["objective_value"] == top["objective_value"]:
            assert r["size"] >= top["size"]


def test_optimizer_objectives_switch():
    from services.simulation import optimize_actions
    rep = _opt_report()
    prof = optimize_actions(rep, scenario="expected", max_actions=4, objective="profit")
    assert prof["best_bundle"]["net_profit_delta"] >= 0
    cash = optimize_actions(rep, scenario="expected", max_actions=4, objective="cash")
    assert cash["best_bundle"]["cash_released"] >= 0


# ── Validation: expanded golden set + judge-vs-human harness ────────────────
def test_golden_set_expanded_and_deterministic_baseline():
    """The deterministic engine must match independent ground-truth ratios on
    every golden case (CI gate; catches extraction/ratio regressions)."""
    from evals.grader import load_cases, grade_deterministic
    cases = load_cases()
    assert len(cases) >= 12
    for c in cases:
        d = grade_deterministic(c)
        assert d["passed"] == d["total"], f"{d['name']} failed: {[k for k in d['checks'] if not k['pass']]}"


def test_validate_judge_harness_with_stub():
    import json
    from evals.grader import validate_judge, load_judge_labels, RUBRIC_CRITERIA
    labels = load_judge_labels()
    assert len(labels) >= 8 and {x["human_label"] for x in labels} == {"strong", "weak"}

    def stub_judge(prompt):  # proxy: a quantified ZAR impact -> high scores
        strong = "financial_impact: R" in prompt
        v = 5 if strong else 2
        d = {c: v for c in RUBRIC_CRITERIA}
        d["comment"] = "x"
        return json.dumps(d)

    out = validate_judge(stub_judge, labels)
    assert out["n"] == len(labels)
    assert out["agreement_pct"] >= 70          # a sensible proxy aligns with human labels
    assert isinstance(out["trustworthy"], bool)


# ── Economics agent + macro stress test (economics x simulator) ────────────
def _macro_report():
    return {
        "industry_key": "manufacturing", "annual_revenue": 20_000_000,
        "imara_score": 52, "financial_fundamentals_score": 48,
        "imara_components": [
            {"label": "Profitability", "weight": 0.25, "value": 45},
            {"label": "Liquidity", "weight": 0.15, "value": 55},
            {"label": "Credit Readiness", "weight": 0.20, "value": 50},
            {"label": "Risk & Compliance", "weight": 0.15, "value": 52},
            {"label": "Market Visibility", "weight": 0.10, "value": 50},
            {"label": "Operational Efficiency", "weight": 0.15, "value": 50}],
        "financial_figures": {"revenue": 20_000_000, "cogs": 15_000_000, "gross_profit": 5_000_000,
                              "operating_profit": 800_000, "interest": 600_000, "net_profit": 150_000,
                              "total_debt": 6_500_000, "opex": 4_200_000, "current_assets": 5_000_000,
                              "current_liabilities": 4_200_000, "equity": 2_500_000,
                              "receivables": 3_200_000, "inventory": 2_600_000},
    }


def test_macro_sensitivity_is_firm_specific():
    from services.macro_data import firm_macro_sensitivity
    r = firm_macro_sensitivity(_macro_report())
    assert r["overall_exposure"] in ("low", "medium", "high")
    assert len(r["drivers"]) == 4 and r["top_driver"]
    for d in r["drivers"]:
        assert d["exposure"] in ("low", "medium", "high") and d["driver"]


def test_macro_stress_three_weighted_scenarios():
    from services.simulation import macro_stress_test
    r = macro_stress_test(_macro_report())
    assert abs(sum(s["weight"] for s in r["scenarios"]) - 1.0) < 1e-6
    assert [s["scenario"] for s in r["scenarios"]] == ["Base", "Adverse", "Upside"]
    assert 0 <= r["macro_resilience"] <= 100 and r["macro_resilience_label"] in ("fragile", "moderate", "robust")
    sc = {s["scenario"]: s for s in r["scenarios"]}
    assert sc["Adverse"]["net_profit"] <= sc["Base"]["net_profit"]          # downside can't raise profit
    assert sc["Upside"]["net_profit"] >= sc["Base"]["net_profit"]


def test_macro_resilience_flags_loss_flip():
    from services.simulation import macro_stress_test
    r = macro_stress_test(_macro_report())
    if r["flips_to_loss_under_adverse"]:
        assert r["macro_resilience"] <= 35 and r["macro_resilience_label"] == "fragile"


def test_economics_agent_sets_deterministic_macro_fields_without_llm():
    from agents.economics_agent import EconomicsAgent
    from memory.shared_memory import SharedMemory
    m = SharedMemory(industry_key="manufacturing", annual_revenue=20_000_000)
    m.financial_figures = _macro_report()["financial_figures"]
    a = EconomicsAgent()
    a._call_claude = lambda *x, **k: "[]"                                   # stub LLM
    a.analyze({}, m)
    assert m.macro_performed is True
    assert m.macro_overall_exposure in ("low", "medium", "high")
    assert m.macro_top_driver and isinstance(m.macro_sensitivity, dict) and m.macro_sensitivity.get("drivers")


# ── Fleet quality (online eval) + error-classified retries ─────────────────
def _qrep(score, conflicts, strong_pct, cost, src="deterministic"):
    return {"imara_score": score, "imara_band": "C",
            "faithfulness_summary": {"conflicts": conflicts, "checked": 10},
            "finding_quality": {"strong_pct": strong_pct, "weak": 2, "total": 20},
            "llm_usage": {"est_cost_usd": cost, "calls": 38},
            "financial_extraction_source": src, "total_runtime_seconds": 600,
            "document_coverage": {"financial": True, "tax": False}}


def test_fleet_extract_metrics():
    from services.fleet_quality import extract_metrics
    m = extract_metrics(_qrep(50, 0, 70, 0.28))
    assert m["imara_score"] == 50 and m["conflicts"] == 0 and m["strong_pct"] == 70
    assert m["doc_types"] == 1 and m["extraction_source"] == "deterministic"


def test_fleet_aggregate_detects_drift():
    from services.fleet_quality import extract_metrics, aggregate
    recent = [{"created_at": "z", "metrics": extract_metrics(_qrep(40, 3, 40, 0.30))} for _ in range(8)]
    baseline = [{"created_at": "a", "metrics": extract_metrics(_qrep(55, 0, 80, 0.28))} for _ in range(12)]
    agg = aggregate(recent + baseline, recent_window=8)
    assert agg["overall"]["runs"] == 20
    assert agg["healthy"] is False and agg["drift_alerts"]
    metrics = {a["metric"] for a in agg["drift_alerts"]}
    assert "avg_imara_score" in metrics and "conflict_rate_pct" in metrics


def test_fleet_healthy_when_stable():
    from services.fleet_quality import extract_metrics, aggregate
    recs = [{"created_at": str(i), "metrics": extract_metrics(_qrep(52, 0, 75, 0.28))} for i in range(20)]
    agg = aggregate(recs, recent_window=8)
    assert agg["healthy"] is True and agg["drift_alerts"] == []


def test_is_transient_error_classification():
    from agents.base_agent import _is_transient
    class RateLimitError(Exception):
        pass
    class _Overloaded(Exception):
        status_code = 529
    class BadRequestError(Exception):
        status_code = 400
    assert _is_transient(RateLimitError()) is True
    assert _is_transient(_Overloaded()) is True
    assert _is_transient(BadRequestError()) is False
    assert _is_transient(ValueError("nope")) is False


# ── Score reason codes (explainability) ────────────────────────────────────
def _reason_report():
    return {"imara_score": 47, "imara_band": "D", "credit_grade": "C",
            "imara_components": [
                {"label": "Profitability", "weight": 0.25, "value": 38},
                {"label": "Credit Readiness", "weight": 0.20, "value": 42},
                {"label": "Risk & Compliance", "weight": 0.15, "value": 55},
                {"label": "Operational Efficiency", "weight": 0.15, "value": 48},
                {"label": "Market Visibility", "weight": 0.10, "value": 60},
                {"label": "Legal Compliance", "weight": 0.15, "value": 92}],
            "financial_ratios": {"net_margin": {"value": 0.9, "benchmark": 7.0},
                                 "debtor_days": {"value": 70, "benchmark": 45}}}


def test_reason_codes_ordered_by_impact_with_drivers():
    from services.reason_codes import reason_codes
    r = reason_codes(_reason_report())
    assert r["available"] is True and r["reasons"]
    impacts = [x["impact"] for x in r["reasons"]]
    assert impacts == sorted(impacts, reverse=True)               # ordered, biggest drag first
    assert r["reasons"][0]["factor"] == "Profitability"           # weight 0.25 x (100-38) is the largest shortfall
    assert "Net margin 0.9%" in r["reasons"][0]["detail"]         # tied to the concrete number
    assert any("Credit grade C" in x["detail"] for x in r["reasons"])


def test_reason_codes_skips_near_perfect_and_lists_strengths():
    from services.reason_codes import reason_codes
    r = reason_codes(_reason_report())
    # Legal Compliance at 92 is a strength, not a principal reason
    assert all(x["factor"] != "Legal Compliance" for x in r["reasons"])
    assert any(s["factor"] == "Legal Compliance" for s in r["strengths"])


def test_reason_codes_handles_no_components():
    from services.reason_codes import reason_codes
    r = reason_codes({"imara_score": 50})
    assert r["available"] is False and r["reasons"] == []


def test_pdf_renders_priority_issues():
    """Regression: _issue_cell was called but never defined, so generate_pdf_report
    crashed (NameError -> 500 without CORS headers -> 'Failed to fetch' in the browser)
    for ANY report containing top_priority_issues — i.e. every real report. Guard it."""
    from services.report_generator import generate_pdf_report
    rep = {
        "business_name": "T", "industry_key": "manufacturing", "currency": "ZAR",
        "imara_score": 38, "imara_band": "D", "executive_summary": "Margin <30% & COGS >70%.",
        "imara_components": [{"label": "Profitability", "weight": 0.25, "value": 38}],
        "top_priority_issues": [
            {"rank": 1, "title": "Gross margin <30% vs >37%", "estimated_total_impact": "R 475 000",
             "why_critical": "COGS > 70% & R&D < 1%", "quick_win": True},
        ],
        # business_model_summary exercises _callout_box; department_findings exercises
        # _collect_all_findings + severity_donut - all three were undefined helpers.
        "business_model_summary": "B2B precision parts < automotive & mining.",
        "quick_wins_narrative": "Quick wins worth > R200k in < 30 days.",
        "department_findings": {"Financial Agent": [
            {"agent": "Financial Agent", "category": "Margin", "severity": "critical",
             "title": "Margin <30% & COGS >70%", "detail": "COGS > 70%.",
             "financial_impact": "R 475 000", "recommendation": "Cut COGS & raise > 5%",
             "roi_estimate": "R 580K", "quick_win": True},
        ]},
        "all_findings_ranked": [],
    }
    for aud in ("owner", "banker", "investor"):
        out = generate_pdf_report(rep, aud)
        assert out and len(out) > 1000


def test_pdf_self_heals_bad_markup_in_findings():
    """Regression: a finding whose AI text contains ReportLab-breaking markup
    (an unclosed <b>, a bare <token, a raw &) must NOT 500 the PDF export.
    This is the exact failure that made owner/investor PDFs return 'Failed to
    fetch' in production while banker (which filtered that finding out) worked.
    The _para() wrapper retries with escaped text instead of crashing."""
    from services.report_generator import generate_pdf_report
    evil = {"agent": "StrategyAgent", "category": "S", "severity": "high",
            "title": "Use <b>bold restructuring",
            "detail": "Unclosed <b>tag; also <EBITDA and a raw & ampersand.",
            "financial_impact": "R 1.2M", "recommendation": "Fix <i>italics",
            "roi_estimate": "R 800K", "benchmark_reference": "<peer", "quick_win": False}
    rep = {"business_name": "T", "industry_key": "manufacturing", "currency": "ZAR",
           "imara_score": 38, "imara_band": "D", "executive_summary": "x",
           "imara_components": [{"label": "P", "weight": 0.25, "value": 40}],
           "department_findings": {"Strategy Agent": [evil]},
           "all_findings_ranked": [evil], "quick_wins": []}
    for aud in ("owner", "investor", "banker"):
        out = generate_pdf_report(rep, aud)
        assert out and len(out) > 1000


# ── Research-cycle builds: distress anchor, bank signals, AHP, fairness, model card ──

def test_altman_z_em_anchor():
    from services.distress_score import altman_z_em
    healthy = {"total_assets": 5_000_000, "current_assets": 2_000_000, "current_liabilities": 800_000,
               "equity": 3_000_000, "retained_earnings": 1_500_000, "operating_profit": 900_000}
    r = altman_z_em(healthy, "B")
    assert r["available"] and r["zone"] == "safe" and r["z_score"] > 2.6
    assert r["convergence"]["agrees"] is True
    distressed = {"total_assets": 3_000_000, "current_assets": 600_000, "current_liabilities": 1_400_000,
                  "equity": 200_000, "retained_earnings": -900_000, "operating_profit": -300_000}
    assert altman_z_em(distressed, "E")["zone"] == "distress"
    # P&L only -> gracefully unavailable, never fabricated
    assert altman_z_em({"revenue": 4_800_000, "operating_profit": 140_000}, "D")["available"] is False


def test_extractor_picks_up_balance_sheet_fields():
    from services.financial_ratios import extract_financials
    figs = extract_financials("Total assets 5,000,000\nTotal liabilities 2,000,000\nRetained earnings 1,500,000\n")
    assert figs.get("total_assets") == 5_000_000
    assert figs.get("total_liabilities") == 2_000_000
    assert figs.get("retained_earnings") == 1_500_000


def test_bank_signals():
    from services.bank_signals import analyze_bank_statement
    stmt = ("Date Description Amount Balance\n"
            "2026-01-03 Salary deposit EFT credit 45,000.00 52,000.00\n"
            "2026-01-09 Debit order RETURNED unpaid R/D -1,500.00 47,300.00\n"
            "2026-02-07 Debit order rent Dr -22,000.00 -9,500.00\n"
            "2026-02-18 Debit order insufficient funds reversal -1,500.00 -11,350.00\n"
            "2026-03-01 Deposit received credit 30,000.00 18,650.00\n")
    r = analyze_bank_statement(stmt)
    assert r["available"] and r["returned_debit_orders"] >= 2
    assert r["negative_balance_rows"] >= 1
    assert r["bank_health_tier"] == "weak" and r["bank_health_score"] < 50
    assert analyze_bank_statement("")["available"] is False


def test_ahp_weight_derivation_consistent():
    from services.ahp import imara_weight_derivation
    d = imara_weight_derivation()
    assert d["consistent"] is True and d["consistency_ratio"] < 0.10
    assert abs(sum(d["derived_weights"].values()) - 1.0) < 1e-6
    w = d["derived_weights"]
    assert w["Profitability"] > w["Credit Readiness"] > w["Legal Compliance"]


def test_bbbee_excluded_from_legal_risk_score():
    """Fairness: a critical B-BBEE finding must NOT drive the legal risk score (and the Imara Score)."""
    from agents.specialist_agents import SALegalAgent
    from memory.shared_memory import SharedMemory, AgentFinding
    agent = SALegalAgent()
    mem = SharedMemory(business_name="T", bbbee_level="Non-Compliant")
    findings = [
        AgentFinding(agent="SA Legal", category="BBBEE", severity="critical",
                     title="B-BBEE non-compliant (Level 8)", detail="Low B-BBEE scorecard limits tenders.",
                     financial_impact="R0", recommendation="x", roi_estimate="x"),
        AgentFinding(agent="SA Legal", category="CIPC", severity="low",
                     title="Annual return due soon", detail="CIPC annual return filing.",
                     financial_impact="R450", recommendation="file", roi_estimate="x"),
    ]
    agent._call_claude = lambda *a, **k: ""
    agent._parse_findings = lambda raw, memory: findings
    agent.analyze({}, mem)
    assert mem.sa_legal_risk_score == 20, mem.sa_legal_risk_score   # 'low' non-BBBEE, NOT critical=85
    assert mem.sa_bbbee_analysis["finding_count"] == 1


def test_model_card_and_governance():
    from services.model_card import model_card
    c = model_card()
    for sec in ("intended_use", "method", "evaluation", "fairness", "limitations", "governance"):
        assert sec in c
    assert c["method"]["weight_derivation"]["consistent"] is True
    from services.score_contract import score_contract
    assert "use_constraints" in score_contract({"imara_score": 50})


# ── Supplier benchmarking feature ──

_ITEMISED_PNL = (
    "Operating Expenses\n"
    "Salaries and wages 1,250,000\n"
    "Rent 240,000\n"
    "Bank charges 62,000\n"
    "Telephone & postage 31,200\n"
    "Fuel and oil 96,500\n"
    "Insurance 54,000\n"
    "Card machine merchant fees 41,800\n"
    "Accounting software Xero 22,000\n"
    "Total operating expenses 2,134,800\n"
)


def test_expense_line_extraction():
    from services.expense_lines import extract_expense_lines
    lines = extract_expense_lines(_ITEMISED_PNL)
    cats = {l["category"] for l in lines}
    assert {"bank_charges", "fuel", "insurance", "card_machine_fees", "telephone_data"} <= cats
    # the 'Total operating expenses' row must be skipped (not double-counted)
    assert not any("total" in l["raw"].lower() for l in lines)
    assert extract_expense_lines("") == []


def test_supplier_benchmark_engine():
    from services.supplier_benchmark import run_supplier_benchmark
    r = run_supplier_benchmark(_ITEMISED_PNL, revenue=4_800_000, profile={"banking_partner": "FNB"})
    assert r["available"] and r["total_expense_lines"] >= 7
    bank = next(o for o in r["opportunities"] if o["category"] == "bank_charges")
    assert bank["incumbent"] == "FNB" and bank["est_saving_low"] > 0      # higher-cost incumbent -> real saving
    assert bank["status"] == "above"
    assert r["total_est_saving_high"] >= r["total_est_saving_low"] > 0
    # only-totals -> gracefully unavailable
    assert run_supplier_benchmark("Total operating expenses 2,000,000", 4_800_000)["available"] is False


def test_supplier_catalog_integrity():
    from services.supplier_catalog import CATALOG, category_reference
    for key in CATALOG:
        ref = category_reference(key)
        assert ref["as_of"] and ref["source"]   # every entry dated + sourced (no naked figures)


def test_supplier_switch_feeds_simulator():
    from services.simulation import derive_actions
    report = {"currency": "ZAR", "industry_key": "manufacturing",
              "financial_figures": {"revenue": 4_800_000, "cogs": 3_480_000, "gross_profit": 1_320_000,
                                    "operating_profit": 520_000, "net_profit": 380_000},
              "financial_ratios": {}, "financial_fundamentals_score": 55,
              "imara_components": [{"label": "Profitability", "weight": 0.25, "value": 55}],
              "supplier_benchmark": {"available": True, "total_est_saving_low": 18_300, "total_est_saving_high": 42_000}}
    assert any(a["id"] == "supplier_switch" and a["driver"] == "opex_reduction_pct" for a in derive_actions(report))


def test_supplier_live_disabled_by_default():
    from services.supplier_live import live_enabled, fetch_live_pricing, augment
    assert live_enabled() is False
    assert fetch_live_pricing("bank_charges", ["TymeBank"])["enabled"] is False
    out = augment({"available": True, "opportunities": []})
    assert out["live"]["enabled"] is False   # no-op, never breaks


# ── Supplier benchmarking robustness fixes ──

def test_expense_lines_current_year_and_no_double_count():
    from services.expense_lines import extract_expense_lines
    # comparative columns: must take the CURRENT-year (first) figure, not the largest
    two = extract_expense_lines("Telephone 28,000 35,000\nBank charges 62,000 58,000\n")
    amt = {r["category"]: r["amount"] for r in two}
    assert amt["telephone_data"] == 28000 and amt["bank_charges"] == 62000
    # summary line + notes breakdown must NOT double-count (keep the largest single row)
    dd = extract_expense_lines("Telephone & data 31,200\nNote 5 Telephone 18,000\nNote 5 Data 13,200\n")
    tel = next(r for r in dd if r["category"] == "telephone_data")
    assert tel["amount"] == 31200


def test_supplier_incumbent_detection_and_suppression():
    from services.supplier_benchmark import run_supplier_benchmark
    r = run_supplier_benchmark(
        "Telephone Vodacom contract 95,000\nInsurance Santam premium 80,000\nBank charges TymeBank 9,000\n",
        4_800_000, profile={})
    by = {o["category"]: o for o in r["opportunities"]}
    assert by["telephone_data"]["incumbent"] == "vodacom" and by["telephone_data"]["est_saving_low"] > 0
    assert by["insurance"]["incumbent"] == "santam" and by["insurance"]["est_saving_low"] > 0
    # already on a low-cost provider -> no switch pushed
    assert by["bank_charges"]["est_saving_low"] is None


def test_supplier_total_savings_realism_cap():
    from services.supplier_benchmark import run_supplier_benchmark
    # wildly above-benchmark lines -> total must be capped at <= 25% of total spend
    stmt = "Bank charges 400,000\nCard machine merchant fees 350,000\nTelephone 300,000\nInsurance 250,000\n"
    r = run_supplier_benchmark(stmt, 4_800_000, profile={"banking_partner": "FNB"})
    total_spend = sum(o["spend"] for o in r["opportunities"])
    assert r["total_est_saving_high"] <= 0.25 * total_spend + 1
    assert "capped_for_realism" in r


def test_simulator_opex_double_count_capped():
    from services.simulation import apply_actions
    report = {"currency": "ZAR", "industry_key": "manufacturing",
              "financial_figures": {"revenue": 4_800_000, "cogs": 3_480_000, "gross_profit": 1_320_000,
                                    "operating_profit": 300_000, "net_profit": 180_000},
              "financial_ratios": {"operating_margin": {"value": 6.25, "benchmark": 12.0}},
              "financial_fundamentals_score": 45,
              "imara_components": [{"label": "Profitability", "weight": 0.25, "value": 45}],
              "supplier_benchmark": {"available": True, "total_est_saving_low": 18_300, "total_est_saving_high": 42_000}}
    s_opex = apply_actions(report, [{"id": "opex", "intensity": 1.0}], "expected")["projected"]["imara_score"]
    s_both = apply_actions(report, [{"id": "opex", "intensity": 1.0}, {"id": "supplier_switch", "intensity": 1.0}],
                           "expected")["projected"]["imara_score"]
    assert s_both <= s_opex + 1   # combined opex reduction capped at max(), not summed
