"""Full-pipeline PRESSURE test (no API spend): drive hostile LLM output + hostile uploaded
data + the alt-data path end-to-end through /api/analyze, and assert the whole pipeline
degrades safely — completes, stays strict-JSON safe (no NaN/inf), injection never renders
raw, and every export + new surface (affordability / alt-data / claim_ledger / audit) survives.
"""
import json
import time
from contextlib import contextmanager

_INJECT = "<script>alert(1)</script>"


class _Usage:
    input_tokens = 900
    output_tokens = 300


class _Msg:
    def __init__(self, text):
        self.content = [type("C", (), {"text": text})()]
        self.usage = _Usage()


def _is_parse(kw):
    p = (kw.get("messages") or [{}])[0].get("content", "")
    return "JSON array of findings" in p or "precision data extractor" in p or "structured findings" in p


class _HostileMessages:
    """Parse calls get non-JSON garbage (forces the generic-finding fallback); analysis calls get
    injection + absurd/huge numbers (stress faithfulness, narrative_claims inf-guard, escaping)."""
    def create(self, **kw):
        if _is_parse(kw):
            return _Msg("not json at all <<< \x07 " + "9" * 300)
        return _Msg("Margin is 999999999% and R" + "9" * 400 + " drain. " + _INJECT
                    + " Breaches Act 999 of 9999. Net profit R-50000000000000.")


class _EmptyMessages:
    def create(self, **kw):
        return _Msg("")            # empty content -> callers must degrade, not crash


class _HostileClient:
    def __init__(self):
        self.messages = _HostileMessages()


class _EmptyClient:
    def __init__(self):
        self.messages = _EmptyMessages()


_HOSTILE_CSV = (
    "Item,Amount\nRevenue," + "9" * 400 + "\nCost of Sales,-99999999999999\nGross Profit,NaN\n"
    "Operating Profit,inf\nNet Profit,not_a_number\nAccounts Receivable,2300000\n"
    "Total Debt," + "9" * 400 + "\nEquity,0\nInterest,inf\n" + "Junk row," + _INJECT + "\n" * 80).encode()

_MOMO = ("\n".join(
    ["2026-0%d-05 MoMo settlement received R 1,200.00" % m for m in (1, 2, 3)]
    + ["2026-0%d-2%d Wallet settlement received R 1,300.00" % (m, m) for m in (1, 2, 3)]
    + ["2026-03-29 Mobile money payout R 990.00"] * 6)).encode()

_GOOD_CSV = (b"Item,Amount\nRevenue,12000000\nCost of Sales,8700000\nOperating Profit,300000\n"
             b"Interest,180000\nNet Profit,120000\nTotal Debt,2200000\nEquity,1800000\n")

_BIG = "9" * 400   # parses to float('inf')
_HOSTILE_TAX = (
    "VAT201 return. Output VAT R" + _INJECT + ", input VAT R-99999999999999.\n"
    "Turnover R" + _BIG + " exceeds the R1m threshold. PAYE EMP201 R inf. Penalty NaN.\n"
    "Provisional IRP6 R-50000000000000. Tax clearance 中文 أمان.\n").encode()
_HOSTILE_LEGAL = (
    "Memorandum of Incorporation. Companies Act 71 of 2008. POPIA 4 of 2013.\n"
    "Director: " + _INJECT + ". Share capital R" + _BIG + ". BBBEE Level inf.\n"
    "CIPC reg 9999/999999/07. Beneficial owners: 中文.\n").encode()
_HOSTILE_HR = (
    "Payroll register. Headcount 99999999999999. Total salaries R-inf.\n"
    "Employee " + _INJECT + ". UIF R NaN. Leave days " + _BIG + ".\n").encode()


@contextmanager
def _pipeline(client_cls, tmp_path, monkeypatch):
    monkeypatch.setenv("BF_DB_PATH", str(tmp_path / "pressure.db"))
    monkeypatch.setenv("MOCK_MODE", "false")
    import agents.base_agent as ba
    saved = ba.client
    ba.client = client_cls()
    from fastapi.testclient import TestClient
    import main
    try:
        with TestClient(main.app) as c:
            yield c
    finally:
        ba.client = saved


def _analyze(c, files, **profile):
    data = {"company_name": "Acme", "industry_key": "retail", "annual_revenue": "12000000",
            "headcount": "12", "currency": "ZAR", "country": "South Africa", "primary_concern": "cash",
            "entity_type": "Private Company (Pty) Ltd", "vat_registered": "no", "years_in_business": "6",
            "consent": "true", "consent_at": "2026-06-21T00:00:00Z", "file_categories": json.dumps(["financial"])}
    data.update(profile)
    r = c.post("/api/analyze", files=files, data=data)
    assert r.status_code == 200, r.text
    aid = r.json()["analysis_id"]
    status = None
    for _ in range(150):
        status = c.get(f"/api/status/{aid}").json().get("status")
        if status in ("complete", "error"):
            break
        time.sleep(0.1)
    return aid, status


def _assert_report_sane(c, aid):
    rep = c.get(f"/api/report/{aid}").json()
    json.dumps(rep, allow_nan=False)                 # strict-JSON safe: NO NaN/inf anywhere
    assert rep.get("imara_score") is not None
    for key in ("affordability", "altdata_signals", "claim_ledger", "audit"):
        assert isinstance(rep.get(key), dict), f"{key} missing/not a dict"
    # exports must all succeed and not leak raw injection
    assert c.get(f"/api/report/{aid}/pdf?audience=banker").content[:4] == b"%PDF"
    assert c.get(f"/api/report/{aid}/reason-letter.pdf").content[:4] == b"%PDF"
    h = c.get(f"/api/report/{aid}/html").text
    assert isinstance(h, str) and _INJECT not in h
    lh = c.get(f"/api/report/{aid}/reason-letter.html").text
    assert _INJECT not in lh
    return rep


def test_hostile_llm_output_degrades_safely(tmp_path, monkeypatch):
    with _pipeline(_HostileClient, tmp_path, monkeypatch) as c:
        aid, status = _analyze(c, {"files": ("fin.csv", _GOOD_CSV, "text/csv")})
        assert status == "complete", f"pipeline did not complete: {status}"
        rep = _assert_report_sane(c, aid)
        # the audit hash chain must still be intact after a hostile run
        assert c.get("/api/admin/audit").json().get("chain", {}).get("intact") is True
        # claim ledger ran over the (hostile) narrative without crashing
        assert "overall" in rep["claim_ledger"]


def test_hostile_financials_degrade_safely(tmp_path, monkeypatch):
    with _pipeline(_HostileClient, tmp_path, monkeypatch) as c:
        aid, status = _analyze(c, {"files": ("fin.csv", _HOSTILE_CSV, "text/csv")})
        assert status == "complete", f"pipeline did not complete: {status}"
        _assert_report_sane(c, aid)


def test_empty_llm_output_degrades_safely(tmp_path, monkeypatch):
    with _pipeline(_EmptyClient, tmp_path, monkeypatch) as c:
        aid, status = _analyze(c, {"files": ("fin.csv", _GOOD_CSV, "text/csv")})
        assert status == "complete", f"pipeline did not complete: {status}"
        _assert_report_sane(c, aid)


def test_altdata_path_lights_up_in_full_report(tmp_path, monkeypatch):
    # a mobile-money statement uploaded as a bank doc -> altdata overlay available end-to-end
    with _pipeline(_HostileClient, tmp_path, monkeypatch) as c:
        files = {"files": ("momo.csv", _MOMO, "text/csv")}
        data_cats = json.dumps(["bank"])
        r = c.post("/api/analyze", files=files,
                   data={"company_name": "Spaza", "industry_key": "retail", "annual_revenue": "0",
                         "headcount": "2", "currency": "ZAR", "country": "South Africa",
                         "primary_concern": "funding", "consent": "true",
                         "consent_at": "2026-06-21T00:00:00Z", "file_categories": data_cats})
        assert r.status_code == 200
        aid = r.json()["analysis_id"]
        status = None
        for _ in range(150):
            status = c.get(f"/api/status/{aid}").json().get("status")
            if status in ("complete", "error"):
                break
            time.sleep(0.1)
        assert status == "complete"
        rep = c.get(f"/api/report/{aid}").json()
        json.dumps(rep, allow_nan=False)
        alt = rep.get("altdata_signals") or {}
        assert alt.get("available") is True and alt.get("channel") == "mobile_money"
        assert 0 <= alt.get("altdata_health_score", -1) <= 100


def test_hostile_multizone_upload_degrades_safely(tmp_path, monkeypatch):
    # financial + tax + legal + hr uploads, ALL hostile (injection / 400-digit / NaN / unicode) —
    # exercises the SATax (2c), SALegal (2d) and HR agent paths, not just financial/bank.
    with _pipeline(_HostileClient, tmp_path, monkeypatch) as c:
        files = [
            ("files", ("fin.csv", _GOOD_CSV, "text/csv")),
            ("files", ("tax.txt", _HOSTILE_TAX, "text/plain")),
            ("files", ("legal.txt", _HOSTILE_LEGAL, "text/plain")),
            ("files", ("hr.txt", _HOSTILE_HR, "text/plain")),
        ]
        data = {"company_name": "Acme", "industry_key": "retail", "annual_revenue": "12000000",
                "headcount": "12", "currency": "ZAR", "country": "South Africa", "primary_concern": "tax",
                "entity_type": "Private Company (Pty) Ltd", "vat_registered": "yes", "years_in_business": "6",
                "consent": "true", "consent_at": "2026-06-21T00:00:00Z",
                "file_categories": json.dumps(["financial", "tax", "legal", "hr"])}
        r = c.post("/api/analyze", files=files, data=data)
        assert r.status_code == 200, r.text
        aid = r.json()["analysis_id"]
        status = None
        for _ in range(180):
            status = c.get(f"/api/status/{aid}").json().get("status")
            if status in ("complete", "error"):
                break
            time.sleep(0.1)
        assert status == "complete", f"multizone pipeline did not complete: {status}"
        _assert_report_sane(c, aid)


def test_hostile_endpoint_params_never_500(tmp_path, monkeypatch):
    with _pipeline(_HostileClient, tmp_path, monkeypatch) as c:
        aid, status = _analyze(c, {"files": ("fin.csv", _GOOD_CSV, "text/csv")})
        assert status == "complete"
        # hostile query params on report endpoints must never 500 (422/200/404 are all fine)
        probes = [
            f"/api/report/{aid}/affordability?proposed_annual_instalment=inf",
            f"/api/report/{aid}/affordability?proposed_annual_instalment=nan",
            f"/api/report/{aid}/affordability?proposed_annual_instalment=-100",
            f"/api/report/{aid}/affordability?proposed_annual_instalment=1e400",
            f"/api/report/{aid}/pdf?audience=" + _INJECT,
            f"/api/report/{aid}/pdf?audience=" + "x" * 500,
            f"/api/report/{aid}/optimize?objective=" + _INJECT,
            f"/api/report/{aid}/optimize?objective=garbage",
            "/api/admin/outcomes?limit=-1",
            "/api/admin/outcomes?limit=999999999",
            "/api/admin/audit?limit=-5",
        ]
        for url in probes:
            assert c.get(url).status_code != 500, f"500 on {url}"
        # hostile POST bodies on the score-contest + outcomes endpoints
        assert c.post(f"/api/report/{aid}/contest",
                      json={"factor": _INJECT, "statement": "x" * 100000, "contact": _INJECT}).status_code != 500
        assert c.post("/api/admin/outcomes",
                      json={"analysis_id": aid, "outcome_type": _INJECT, "label": 99, "value": "inf"}).status_code != 500
