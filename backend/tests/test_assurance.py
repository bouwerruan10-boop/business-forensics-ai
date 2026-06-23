"""Tests for the deterministic assurance / PIS / CIPC engine (services/assurance.py)."""
from services.assurance import assess, public_interest_score, cipc_compliance


def test_pis_small_owner_managed_company_needs_only_review_or_compilation():
    r = assess(headcount=22, annual_revenue=8_450_000,
               financial_figures={"total_liabilities": 3_380_000, "revenue": 8_450_000},
               entity_type="Private Company (Pty) Ltd", cipc_number="2018/345678/07")
    assert r["available"] is True
    # 22 employees + ceil(8.45)=9 + ceil(3.38)=4 = 35
    assert r["public_interest_score"] == 35
    assert r["recommended_tier"] == "independent review"
    assert r["is_mandatory"] is False
    # owner-managed exemption note must be surfaced (the cost-saving insight)
    assert any("OWNER-MANAGED" in n for n in r["notes"])
    assert r["potential_saving"]
    assert r["cipc"]["registration_year"] == 2018 and r["cipc"]["valid_format"] is True


def test_pis_350_or_more_forces_audit():
    r = assess(headcount=300, annual_revenue=60_000_000,
               financial_figures={"total_liabilities": 0}, entity_type="Private Company (Pty) Ltd")
    assert r["public_interest_score"] >= 350
    assert r["recommended_tier"] == "audit" and r["is_mandatory"] is True


def test_public_company_always_audit():
    r = assess(headcount=5, annual_revenue=1_000_000, entity_type="Public Company (Ltd)")
    assert r["recommended_tier"] == "audit" and r["is_mandatory"] is True


def test_part_thereof_rounds_up():
    assert public_interest_score(0, 1_000_000, 0)["pis"] == 1
    assert public_interest_score(0, 1_000_001, 0)["pis"] == 2   # 'or part thereof'
    assert public_interest_score(0, 0, 1)["pis"] == 1           # 1 point per R1m liability part


def test_missing_inputs_returns_unavailable_not_a_crash():
    r = assess(headcount=0, annual_revenue=0, financial_figures={})
    assert r["available"] is False and "reason" in r


def test_cipc_invalid_or_missing_number_flags():
    assert cipc_compliance("", "")["valid_format"] is False
    assert cipc_compliance("", "")["flag"]
    assert cipc_compliance("not-a-number", "")["valid_format"] is False
    ok = cipc_compliance("2016/204815/07", "Pty Ltd")
    assert ok["valid_format"] is True and ok["registration_year"] == 2016


def test_adversarial_hostile_inputs_never_raise():
    # None / garbage / formatted strings / negatives / huge — all must be handled
    assess(headcount=None, annual_revenue="garbage",
           financial_figures={"total_liabilities": "R 3 380 000"},
           entity_type=None, cipc_number=None)
    assess(headcount=-5, annual_revenue=-100, financial_figures={"total_liabilities": -1},
           entity_type="", cipc_number="x/y/z")
    assess(headcount=10**9, annual_revenue=10**18, financial_figures={"total_liabilities": 10**18},
           entity_type="Pty", cipc_number="2020/1/07")
    public_interest_score(beneficial_owners="lots")   # bad type tolerated


def test_pipeline_and_endpoint_wire_assurance_through(monkeypatch, tmp_path):
    """No-API: assurance is attached to the report and served by /assurance."""
    import json, time, os
    os.environ["BF_DB_PATH"] = str(tmp_path / "t.db")
    import agents.base_agent as ba

    class _U: input_tokens = 100; output_tokens = 50
    class _C:
        def __init__(s, t): s.text = t
    class _M:
        def __init__(s, t): s.content = [_C(t)]; s.usage = _U()
    finds = json.dumps([{"category": "Cash Flow", "severity": "high", "title": "Slow receivables",
                         "detail": "Debtor days high.", "financial_impact": "R 100 000",
                         "recommendation": "Tighten", "roi_estimate": "R 100k", "cost_of_inaction": "x",
                         "benchmark_reference": "y", "data_source": "financials", "quick_win": False}])
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
        csv = b"Account,Amount\nRevenue,8450000\nTotal Liabilities,3380000\nNet Profit,130000\n"
        with TestClient(main.app) as c:
            r = c.post("/api/analyze", files={"files": ("f.csv", csv, "text/csv")},
                       data={"company_name": "Assur Co", "industry_key": "retail", "annual_revenue": "8450000",
                             "headcount": "22", "entity_type": "Private Company (Pty) Ltd",
                             "cipc_number": "2018/345678/07", "consent": "true",
                             "consent_at": "2026-06-23T00:00:00Z", "file_categories": json.dumps(["financial"])})
            aid = r.json()["analysis_id"]
            for _ in range(120):
                if c.get(f"/api/status/{aid}").json().get("status") in ("complete", "error"):
                    break
                time.sleep(0.1)
            rep = c.get(f"/api/report/{aid}").json()
            assert rep.get("assurance", {}).get("available") is True
            assert rep["assurance"]["recommended_tier"] in ("audit", "independent review", "compilation")
            ep = c.get(f"/api/report/{aid}/assurance").json()
            assert ep["public_interest_score"] == rep["assurance"]["public_interest_score"]
    finally:
        ba.client = saved
