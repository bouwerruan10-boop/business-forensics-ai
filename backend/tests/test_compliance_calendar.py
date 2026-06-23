"""Tests for the deterministic statutory compliance calendar."""
from services.compliance_calendar import build_compliance_calendar


def _co(**kw):
    base = {"annual_revenue": 8450000, "headcount": 22, "vat_registered": "yes",
            "entity_type": "Private Company (Pty) Ltd", "cipc_number": "2018/345678/07",
            "bbbee_level": "Level 4", "tax_year_end": "February (SARS default)"}
    base.update(kw)
    return base


def test_full_company_obligations_and_free_wins():
    m = build_compliance_calendar(_co())
    assert m["available"] is True
    titles = [o["title"] for o in m["obligations"]]
    assert any("CIPC annual return" in t for t in titles)
    assert any("VAT201" in t for t in titles)            # vat registered
    assert any("EMP201" in t for t in titles)            # has employees
    assert any("ITR14" in t or "IT14" in t for t in titles)
    # FREE on-ramps surfaced
    free = {w["title"] for w in m["free_quick_wins"]}
    assert any("EME affidavit" in t for t in free)       # turnover < R10m
    assert any("Information Officer" in t for t in free)  # POPIA, always


def test_compulsory_vat_gap_is_top_priority():
    m = build_compliance_calendar(_co(vat_registered="no"))   # rev > R1m but not registered
    assert m["obligations"][0]["priority"] == "critical"
    assert "VAT registration" in m["obligations"][0]["title"]


def test_no_employees_drops_payroll():
    m = build_compliance_calendar(_co(headcount=0))
    assert not any("EMP201" in o["title"] for o in m["obligations"])


def test_vat_not_registered_below_threshold_no_vat_obligation_no_gap():
    m = build_compliance_calendar(_co(vat_registered="no", annual_revenue=600000))
    titles = [o["title"] for o in m["obligations"]]
    assert not any("VAT201" in t for t in titles)
    assert not any("VAT registration" in t for t in titles)   # below R1m -> not compulsory


def test_bbbee_tiers():
    assert any("EME affidavit" in o["title"] for o in build_compliance_calendar(_co(annual_revenue=5_000_000))["obligations"])
    assert any("QSE" in o["title"] for o in build_compliance_calendar(_co(annual_revenue=30_000_000))["obligations"])
    assert any("verification certificate" in o["title"] for o in build_compliance_calendar(_co(annual_revenue=80_000_000))["obligations"])


def test_empty_or_non_dict_unavailable():
    assert build_compliance_calendar({}).get("available") is False
    assert build_compliance_calendar(None).get("available") is False


def test_adversarial_never_raises():
    build_compliance_calendar({"annual_revenue": "garbage", "headcount": None, "vat_registered": 5,
                               "entity_type": None, "cipc_number": 12345, "tax_year_end": "xx"})
    build_compliance_calendar({"annual_revenue": -1, "headcount": -5, "tax_year_end": "February"})


def test_pipeline_and_endpoint_wire(monkeypatch, tmp_path):
    import json, time, os
    os.environ["BF_DB_PATH"] = str(tmp_path / "t.db")
    import agents.base_agent as ba

    class _U: input_tokens = 100; output_tokens = 50
    class _C:
        def __init__(s, t): s.text = t
    class _M:
        def __init__(s, t): s.content = [_C(t)]; s.usage = _U()
    finds = json.dumps([{"category": "Tax", "severity": "high", "title": "x", "detail": "d",
                         "financial_impact": "R 1", "recommendation": "r", "roi_estimate": "R 1",
                         "cost_of_inaction": "x", "benchmark_reference": "y", "data_source": "tax",
                         "quick_win": False}])
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
        with TestClient(main.app) as c:
            r = c.post("/api/analyze", files={"files": ("f.csv", b"Account,Amount\nRevenue,8450000\n", "text/csv")},
                       data={"company_name": "Cal Co", "industry_key": "retail", "annual_revenue": "8450000",
                             "headcount": "12", "entity_type": "Private Company (Pty) Ltd",
                             "cipc_number": "2018/345678/07", "vat_registered": "yes",
                             "tax_year_end": "February", "bbbee_level": "Level 4", "consent": "true",
                             "consent_at": "2026-06-23T00:00:00Z", "file_categories": json.dumps(["financial"])})
            aid = r.json()["analysis_id"]
            for _ in range(120):
                if c.get(f"/api/status/{aid}").json().get("status") in ("complete", "error"):
                    break
                time.sleep(0.1)
            rep = c.get(f"/api/report/{aid}").json()
            assert rep.get("compliance_calendar", {}).get("available") is True
            ep = c.get(f"/api/report/{aid}/compliance-calendar").json()
            assert ep["count"] == rep["compliance_calendar"]["count"]
    finally:
        ba.client = saved
