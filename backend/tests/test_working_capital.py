"""Tests for the deterministic working-capital / cash-conversion-cycle engine."""
from services.working_capital import build_working_capital


def _rep(inv=82, inv_b=45, deb=70, deb_b=35, cre=60, cre_b=35, cogs=5915000, rev=8450000):
    ratios = {}
    if inv is not None:
        ratios["inventory_days"] = {"value": inv, "benchmark": inv_b}
    if deb is not None:
        ratios["debtor_days"] = {"value": deb, "benchmark": deb_b}
    if cre is not None:
        ratios["creditor_days"] = {"value": cre, "benchmark": cre_b}
    return {"financial_ratios": ratios, "financial_figures": {"cogs": cogs, "revenue": rev}}


def test_ccc_and_release_computed():
    m = build_working_capital(_rep())
    assert m["available"] is True
    # CCC = 82 + 70 - 60 = 92 vs bench 45 + 35 - 35 = 45
    assert m["cash_conversion_cycle"]["value"] == 92.0
    assert m["cash_conversion_cycle"]["benchmark"] == 45.0
    assert m["cash_conversion_cycle"]["status"] == "critical"
    # inventory excess 37d/365*5.915m ~599.6k; debtor excess 35d/365*8.45m ~810.3k
    rel = m["working_capital_release"]
    assert 1_400_000 < rel["total"] < 1_420_000
    assert {i["driver"] for i in rel["items"]} == {"Inventory", "Receivables"}


def test_no_excess_means_no_trapped_cash():
    m = build_working_capital(_rep(inv=40, deb=30, cre=40))  # at/below benchmark
    assert m["working_capital_release"]["total"] == 0.0
    assert m["working_capital_release"]["items"] == []
    assert m["cash_conversion_cycle"]["status"] == "good"


def test_partial_legs_still_work():
    m = build_working_capital(_rep(cre=None))  # no creditor days
    assert m["available"] is True
    assert "payables" not in m["cash_conversion_cycle"]["legs_available"]
    assert m["cash_conversion_cycle"]["components"]["creditor_days"] is None


def test_missing_both_inventory_and_debtor_unavailable():
    m = build_working_capital(_rep(inv=None, deb=None))
    assert m["available"] is False


def test_adversarial_inputs_never_raise():
    build_working_capital({"financial_ratios": {"inventory_days": {"value": "junk", "benchmark": None}},
                           "financial_figures": {"cogs": "R 1 000", "revenue": None}})
    build_working_capital({"financial_ratios": {"debtor_days": {"value": -10, "benchmark": -5}},
                           "financial_figures": {"revenue": float("inf")}})
    assert build_working_capital(None).get("available") is False
    assert build_working_capital({}).get("available") is False


def test_pipeline_and_endpoint_wire(monkeypatch, tmp_path):
    import json, time, os
    os.environ["BF_DB_PATH"] = str(tmp_path / "t.db")
    import agents.base_agent as ba

    class _U: input_tokens = 100; output_tokens = 50
    class _C:
        def __init__(s, t): s.text = t
    class _M:
        def __init__(s, t): s.content = [_C(t)]; s.usage = _U()
    finds = json.dumps([{"category": "Cash Flow", "severity": "high", "title": "Slow stock",
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
        csv = (b"Account,Amount\nRevenue,8450000\nCost of Sales,5915000\nInventory,1340000\n"
               b"Trade Receivables,1620000\nTrade Payables,1180000\n")
        with TestClient(main.app) as c:
            r = c.post("/api/analyze", files={"files": ("f.csv", csv, "text/csv")},
                       data={"company_name": "WC Co", "industry_key": "retail", "annual_revenue": "8450000",
                             "headcount": "12", "consent": "true", "consent_at": "2026-06-23T00:00:00Z",
                             "file_categories": json.dumps(["financial"])})
            aid = r.json()["analysis_id"]
            for _ in range(120):
                if c.get(f"/api/status/{aid}").json().get("status") in ("complete", "error"):
                    break
                time.sleep(0.1)
            rep = c.get(f"/api/report/{aid}").json()
            assert "working_capital" in rep
            ep = c.get(f"/api/report/{aid}/working-capital").json()
            assert "cash_conversion_cycle" in ep or ep.get("available") is False
    finally:
        ba.client = saved
