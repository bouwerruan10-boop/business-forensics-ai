"""
Full-pipeline integration smoke test with NO API key / NO API spend.

Injects a fake Claude client (returns canned findings) and drives the real
/api/analyze endpoint end-to-end through TestClient, then asserts the whole
report assembled and that the five deep builds are wired through to the API:
  - Build 3 (observability): report.llm_usage with per-model token/cost
  - Build 4 (self-critique): report.finding_quality + per-finding quality tier
  - Build 1 (RAG grounding): a finding cites a real SA Act
  - Build 5 (optimiser): /optimize returns a best bundle for all objectives
This guards against integration regressions that unit tests miss.
"""
import json
import re
import time

import pytest


class _Usage:
    input_tokens = 1300
    output_tokens = 450


class _C:
    def __init__(self, text):
        self.text = text


class _Msg:
    def __init__(self, text):
        self.content = [_C(text)]
        self.usage = _Usage()


_FINDINGS = json.dumps([
    {"category": "Tax", "severity": "critical", "title": "VAT registration overdue",
     "detail": "Turnover R12,000,000 exceeds the R1m threshold but the business is not VAT registered, breaching VAT Act 89 of 1991 s23.",
     "financial_impact": "R 240 000 penalty + interest exposure", "recommendation": "Register for VAT within 21 business days via SARS eFiling",
     "roi_estimate": "Avoids R 240 000 penalty", "cost_of_inaction": "Penalties compound monthly", "benchmark_reference": "VAT Act 89 of 1991, s23",
     "data_source": "financials", "quick_win": True},
    {"category": "Cash Flow", "severity": "high", "title": "Slow receivables collection",
     "detail": "Debtor days ~70 vs sector 45, tying up cash.", "financial_impact": "R 450 000 cash locked up",
     "recommendation": "Tighten collections to net-45 with deposit terms", "roi_estimate": "R 450 000 freed", "cost_of_inaction": "Ongoing cash strain",
     "benchmark_reference": "Sector debtor days 45", "data_source": "financials", "quick_win": False},
    {"category": "Risk", "severity": "high", "title": "Concentration risk",
     "detail": "Vague exposure to a single channel.", "financial_impact": "Unquantified",
     "recommendation": "Review", "roi_estimate": "TBD with client", "cost_of_inaction": "",
     "benchmark_reference": "see analysis above", "data_source": "plan", "quick_win": False},
])


class _Messages:
    def create(self, **kw):
        msgs = kw.get("messages", [{}])
        prompt = msgs[0].get("content", "") if msgs else ""
        if "JSON array of findings" in prompt or "precision data extractor" in prompt:
            return _Msg(_FINDINGS)
        return _Msg("Analysis: gross margin 27.5% vs sector 34%; VAT Act 89 of 1991 s23 exposure; R 450 000 cash drain.")


class _FakeClient:
    def __init__(self):
        self.messages = _Messages()


_CSV = (b"Item,Amount\nRevenue,12000000\nCost of Sales,8700000\nGross Profit,3300000\n"
        b"Operating Expenses,3000000\nOperating Profit,300000\nInterest,180000\nNet Profit,120000\n"
        b"Accounts Receivable,2300000\nInventory,1900000\nCurrent Assets,4600000\n"
        b"Current Liabilities,3100000\nAccounts Payable,1400000\nTotal Debt,2200000\nEquity,1800000\n")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BF_DB_PATH", str(tmp_path / "test.db"))
    import agents.base_agent as ba
    saved = ba.client
    ba.client = _FakeClient()            # no API; canned responses
    from fastapi.testclient import TestClient
    import main
    with TestClient(main.app) as c:      # context manager fires startup -> init_db
        yield c
    ba.client = saved                    # restore for other tests


def test_full_pipeline_no_api(client):
    data = {"company_name": "Acme Trading (Pty) Ltd", "industry_key": "retail", "annual_revenue": "12000000",
            "headcount": "12", "currency": "ZAR", "country": "South Africa", "primary_concern": "VAT and cash flow",
            "entity_type": "Private Company (Pty) Ltd", "vat_registered": "no", "bbbee_level": "Level 4",
            "years_in_business": "6", "consent": "true", "consent_at": "2026-06-21T00:00:00Z",
            "file_categories": json.dumps(["financial"])}
    r = client.post("/api/analyze", files={"files": ("financials.csv", _CSV, "text/csv")}, data=data)
    assert r.status_code == 200
    aid = r.json()["analysis_id"]

    status = None
    for _ in range(80):
        status = client.get(f"/api/status/{aid}").json().get("status")
        if status in ("complete", "error"):
            break
        time.sleep(0.1)
    assert status == "complete"

    rep = client.get(f"/api/report/{aid}").json()
    assert rep.get("imara_score") is not None
    assert rep.get("financial_ratios") and rep.get("all_findings_ranked")

    # Tax Optimisation agent ("Tax Me If You Can") wired end-to-end
    topt = rep.get("tax_optimization") or {}
    assert topt.get("available") is True
    assert topt.get("total_saving_high", 0) > 0   # SBC saving quantified for this Pty Ltd
    assert any("Small Business Corporation" in o["name"] for o in topt["opportunities"])
    assert "not tax advice" in topt.get("disclaimer", "").lower()

    # Build 3 — observability
    usage = rep.get("llm_usage")
    assert isinstance(usage, dict) and usage.get("calls", 0) > 0 and usage.get("by_model")

    # Build 4 — self-critique
    fq = rep.get("finding_quality")
    assert isinstance(fq, dict) and fq.get("total", 0) > 0
    assert any("quality" in f for f in rep["all_findings_ranked"])

    # Build 1 — grounding produced a real Act citation
    assert any(re.search(r"Act \d+ of \d{4}", (f.get("detail", "") + f.get("benchmark_reference", "")))
               for f in rep["all_findings_ranked"])

    # Build 5 — optimiser endpoint, all objectives
    for obj in ("imara", "profit", "cash"):
        o = client.get(f"/api/report/{aid}/optimize?objective={obj}")
        assert o.status_code == 200 and o.json().get("best_bundle")

    # usage endpoint passthrough
    assert client.get(f"/api/report/{aid}/usage").json().get("llm_usage")

    # Economics agent ran in the pipeline + macro overlay endpoint works
    assert rep.get("macro_performed") is True
    assert rep.get("macro_overall_exposure") in ("low", "medium", "high")
    macro = client.get(f"/api/report/{aid}/macro")
    assert macro.status_code == 200
    mj = macro.json()
    assert mj["sensitivity"]["drivers"] and len(mj["stress_test"]["scenarios"]) == 3
    assert 0 <= mj["stress_test"]["macro_resilience"] <= 100

    # Reason codes (explainability) + Fleet Quality online monitor
    reasons = client.get(f"/api/report/{aid}/reasons").json()
    assert reasons["available"] is True and reasons["reasons"]
    imp = [x["impact"] for x in reasons["reasons"]]
    assert imp == sorted(imp, reverse=True)
    fq = client.get("/api/admin/fleet-quality")
    assert fq.status_code == 200
    assert fq.json()["overall"]["runs"] >= 1 and "drift_alerts" in fq.json()

    # Regression: Action Simulator endpoints must accept the REAL frontend payload
    # (no "variable" field) — this 422'd in production before ActionSimRequest.variable
    # was made optional.
    sa = client.post("/api/simulate/actions", json={"analysis_id": aid, "actions": [], "scenario": "expected"})
    assert sa.status_code == 200, sa.text
    mc = client.post("/api/simulate/montecarlo", json={"analysis_id": aid, "actions": []})
    assert mc.status_code == 200, mc.text

    # Research-cycle builds: distress anchor, bank signals, model card
    assert client.get(f"/api/report/{aid}/distress").status_code == 200
    assert client.get(f"/api/report/{aid}/bank-signals").status_code == 200
    # research-driven "Lender's-Eye View" builds wired through to the API
    lv = client.get(f"/api/report/{aid}/lender-view").json()
    assert lv.get("available") and lv.get("decline_risk") in ("low", "medium", "high")
    assert client.get(f"/api/report/{aid}/normalization").status_code == 200
    assert client.get(f"/api/report/demo-001/lender-view").json().get("decline_risk") in ("low", "medium", "high")
    brp = client.get("/api/report/demo-001/bank-ready-pack")
    assert brp.status_code == 200 and brp.content[:4] == b"%PDF"
    aud = client.get(f"/api/report/{aid}/audit").json()
    assert aud.get("available") and aud["records"][0].get("record_hash")
    assert client.get("/api/admin/audit").json().get("chain", {}).get("intact") is True
    ff = client.get(f"/api/report/{aid}/funding-fit").json()
    assert ff.get("available") and "options" in ff and ff["gate"]["status"] in ("application-ready", "strengthen-first")
    mcd = client.get("/api/v1/model-card")
    assert mcd.status_code == 200 and mcd.json()["method"]["weight_derivation"]["consistent"] is True
    assert client.get(f"/api/report/{aid}/supplier-savings").status_code == 200

    # Validation harness: record an outcome + admin validation/calibration endpoints respond
    ro = client.post("/api/admin/outcomes", json={"analysis_id": aid, "outcome_type": "default", "label": 1})
    assert ro.status_code == 200 and ro.json()["recorded"] is True
    assert client.get("/api/admin/validation").status_code == 200
    cal = client.get("/api/admin/calibration")
    assert cal.status_code == 200 and "calibrated" in cal.json()
