"""Tests for the deterministic 5-Cs + DSCR credit memo (services/credit_memo.py)."""
from services.credit_memo import build_credit_memo, _dscr


def _base():
    return {
        "financial_figures": {"ebitda": 400000, "operating_profit": 300000, "interest": 50000,
                              "total_debt": 500000, "equity": 1500000, "total_assets": 4000000,
                              "current_assets": 2500000, "inventory": 800000, "receivables": 900000},
        "financial_ratios": {"debt_to_equity": {"value": 1.2}},
        "normalization": {"adjusted_ebitda_low": 380000},
        "bank_signals": {"available": True, "returned_debit_orders": 0, "negative_balance_rows": 0},
        "lender_view": {"decline_risk": "low"},
        "credit_grade": "B", "sa_tax_clearance_status": "valid", "sa_vat_status": "compliant",
        "macro_overall_exposure": "medium",
    }


def test_healthy_file_progresses_and_dscr_passes():
    m = build_credit_memo(_base())
    assert m["available"] is True
    assert m["dscr"]["value"] >= 1.25 and m["dscr"]["status"] == "pass"  # 380k / (50k + 100k) = 2.53
    statuses = {c["c"]: c["status"] for c in m["five_cs"]}
    assert statuses["Capacity"] == "pass" and statuses["Capital"] == "pass"
    assert "PROGRESS" in m["committee_read"]
    assert len(m["five_cs"]) == 5


def test_high_debt_service_fails_capacity_and_declines():
    r = _base()
    r["financial_figures"]["interest"] = 198000
    r["financial_figures"]["total_debt"] = 2200000   # service = 198k + 440k = 638k; 380k/638k = 0.6
    r["normalization"] = {"adjusted_ebitda_low": 380000}
    m = build_credit_memo(r)
    assert m["dscr"]["status"] == "fail"
    assert any(c["c"] == "Capacity" and c["status"] == "fail" for c in m["five_cs"])
    assert "DECLINE" in m["committee_read"]


def test_negative_equity_fails_capital():
    r = _base(); r["financial_figures"]["equity"] = -100000; r["financial_ratios"] = {}
    m = build_credit_memo(r)
    assert any(c["c"] == "Capital" and c["status"] == "fail" for c in m["five_cs"])


def test_bounced_debit_order_fails_character():
    r = _base(); r["bank_signals"]["returned_debit_orders"] = 2
    m = build_credit_memo(r)
    assert any(c["c"] == "Character" and c["status"] == "fail" for c in m["five_cs"])


def test_no_assets_flags_collateral():
    r = _base()
    for k in ("total_assets", "current_assets", "inventory", "receivables"):
        r["financial_figures"][k] = 0
    m = build_credit_memo(r)
    assert any(c["c"] == "Collateral" and c["status"] == "watch" for c in m["five_cs"])


def test_no_existing_debt_assesses_on_ebitda():
    r = _base(); r["financial_figures"]["interest"] = 0; r["financial_figures"]["total_debt"] = 0
    d = _dscr(r["financial_figures"], r["normalization"])
    assert d["status"] == "pass" and d["value"] is None  # no debt service -> capacity on EBITDA


def test_empty_or_non_dict_report_is_safe():
    assert build_credit_memo({}).get("available") is False
    assert build_credit_memo(None).get("available") is False


def test_adversarial_hostile_figures_never_raise():
    build_credit_memo({"financial_figures": {"ebitda": "garbage", "interest": None, "total_debt": "(R 1 000)",
                       "equity": float("nan"), "total_assets": "x"}, "bank_signals": {"available": True}})
    build_credit_memo({"financial_figures": {"ebitda": -10**18, "interest": -1, "total_debt": -5},
                       "financial_ratios": {"debt_to_equity": {"value": "bad"}}})


def test_pipeline_and_endpoint_wire_credit_memo(monkeypatch, tmp_path):
    import json, time, os
    os.environ["BF_DB_PATH"] = str(tmp_path / "t.db")
    import agents.base_agent as ba

    class _U: input_tokens = 100; output_tokens = 50
    class _C:
        def __init__(s, t): s.text = t
    class _M:
        def __init__(s, t): s.content = [_C(t)]; s.usage = _U()
    finds = json.dumps([{"category": "Cash Flow", "severity": "high", "title": "Slow receivables",
                         "detail": "d", "financial_impact": "R 100 000", "recommendation": "r",
                         "roi_estimate": "R 100k", "cost_of_inaction": "x", "benchmark_reference": "y",
                         "data_source": "financials", "quick_win": False}])
    class _Ms:
        def create(s, **kw):
            p = (kw.get("messages", [{}])[0].get("content", "")) if kw.get("messages") else ""
            return _M(finds) if ("JSON array of findings" in p or "precision data extractor" in p) else _M("Analysis.")
    class _Fk:
        def __init__(s): s.messages = _Ms()
    saved = ba.client; ba.client = _Fk()
    try:
        from fastapi.testclient import TestClient
        import main
        csv = b"Account,Amount\nRevenue,8450000\nOperating Profit,300000\nInterest,198000\nTotal Debt,2200000\nTotal Assets,4952000\nCurrent Assets,3102000\nEquity,1572000\n"
        with TestClient(main.app) as c:
            r = c.post("/api/analyze", files={"files": ("f.csv", csv, "text/csv")},
                       data={"company_name": "Memo Co", "industry_key": "retail", "annual_revenue": "8450000",
                             "headcount": "12", "consent": "true", "consent_at": "2026-06-23T00:00:00Z",
                             "file_categories": json.dumps(["financial"])})
            aid = r.json()["analysis_id"]
            for _ in range(120):
                if c.get(f"/api/status/{aid}").json().get("status") in ("complete", "error"):
                    break
                time.sleep(0.1)
            rep = c.get(f"/api/report/{aid}").json()
            assert rep.get("credit_memo", {}).get("available") is True
            assert len(rep["credit_memo"]["five_cs"]) == 5
            ep = c.get(f"/api/report/{aid}/credit-memo").json()
            assert ep["committee_read"] == rep["credit_memo"]["committee_read"]
    finally:
        ba.client = saved
