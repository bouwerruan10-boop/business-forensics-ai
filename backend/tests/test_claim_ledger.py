"""Claim/Evidence contract tests: uniform claim, narrative number verification, ledger."""
from fastapi.testclient import TestClient

from services.claim_contract import make_claim, verify_metric, verify_currency
from services.narrative_claims import verify_narrative
from services.claim_ledger import build_claim_ledger, record_claim_ledger


# ---- claim_contract ----

def test_verify_metric_conflict_verified_unverified():
    assert verify_metric(21.3, 33.2, "%", "gross margin")[0] == "conflict"
    assert verify_metric(33.0, 33.2, "%", "gross margin")[0] == "verified"   # within tolerance
    assert verify_metric(50, None, "days")[0] == "unverified"


def test_verify_currency_matches_known_figure():
    status, _, src = verify_currency(450_000, {"net_profit": 450_000, "revenue": 5_000_000})
    assert status == "verified" and src == "net_profit"
    assert verify_currency(1_200_000, {"revenue": 5_000_000})[0] == "unverified"


def test_make_claim_normalises():
    c = make_claim("x", "bogus_kind", value=1, verification="nonsense")
    assert c["kind"] == "qualitative"           # unknown kind -> qualitative
    assert c["verification"] == "unverified"    # unknown status -> unverified


# ---- narrative_claims ----

_REPORT = {
    "financial_ratios": {"gross_margin": {"value": 33.2, "label": "gross margin"},
                         "debtor_days": {"value": 52, "label": "debtor days"}},
    "financial_figures": {"revenue": 5_000_000, "net_profit": 450_000},
    "annual_revenue": 5_000_000,
    "executive_summary": ("The business runs a gross margin of 21.3% and debtor days of 52. "
                          "Net profit was R450,000 and there is a R1.2 million working-capital opportunity."),
    "systemic_themes": [{"title": "Working capital", "narrative": "Material.", "combined_impact": "R1.2 million per year"}],
}


def test_narrative_flags_conflict_and_unverified():
    r = verify_narrative(_REPORT)
    assert r["available"] is True
    # the LLM's 21.3% margin conflicts with the computed 33.2%
    assert any(c["kind"] == "metric" and c["verification"] == "conflict" for c in r["claims"])
    # the debtor days and the R450,000 match computed values
    assert any(c["verification"] == "verified" for c in r["claims"])
    # the R1.2m opportunity is not traceable -> unverified, never a silent pass
    assert any(c["kind"] == "currency" and c["verification"] == "unverified" for c in r["claims"])


def test_narrative_robust_to_hostile():
    assert verify_narrative("x")["available"] is False
    assert verify_narrative(None)["summary"] == {}
    assert verify_narrative({})["summary"]["total"] == 0


# ---- claim_ledger ----

def test_ledger_overall_states():
    assert build_claim_ledger(_REPORT)["overall"] == "conflicts_present"
    clean = {"financial_ratios": {}, "financial_figures": {"revenue": 5_000_000},
             "executive_summary": "Revenue is R5,000,000."}
    assert build_claim_ledger(clean)["overall"] == "all_clear"
    est = {"financial_ratios": {}, "financial_figures": {}, "executive_summary": "An opportunity of R2 million exists."}
    assert build_claim_ledger(est)["overall"] == "unverified_present"


def test_ledger_folds_finding_signals():
    rep = dict(_REPORT)
    rep["faithfulness_summary"] = {"checked": 8, "confirmed": 7, "conflicts": 1, "benchmark_conflicts": 0}
    rep["finding_quality"] = {"strong": 5, "adequate": 3, "weak": 1}
    led = build_claim_ledger(rep)
    assert led["findings"]["checked"] == 8 and led["findings"]["conflicts"] == 1
    assert led["quality"]["weak"] == 1
    assert "verified against your computed data" in led["headline"]


def test_ledger_robust():
    assert build_claim_ledger("x")["available"] is False
    assert build_claim_ledger(None)["available"] is False


def test_ledger_record_is_immutable(tmp_path, monkeypatch):
    import services.database as db
    monkeypatch.setattr(db, "_DB_PATH", tmp_path / "ledger.db")
    db.init_db()
    res = record_claim_ledger("a-cl", build_claim_ledger(_REPORT))
    assert res["recorded"] is True and res["record_hash"]
    rows = [r for r in db.get_audit("a-cl") if r.get("type") == "claim_ledger"]
    assert len(rows) == 1
    assert db.verify_audit_chain()["intact"] is True


# ---- endpoint + serialization ----

def test_endpoint_returns_ledger():
    import main
    main.analyses["t-claim-ledger"] = dict(_REPORT)
    try:
        client = TestClient(main.app)
        res = client.get("/api/report/t-claim-ledger/claim-ledger")
        assert res.status_code == 200
        assert res.json()["overall"] == "conflicts_present"
    finally:
        main.analyses.pop("t-claim-ledger", None)


def test_evidence_plain_language_now_serialised():
    # the finding serialiser must now include the (previously dropped) evidence field
    import agents.ceo_agent as ce
    import inspect
    src = inspect.getsource(ce.CEOAgent._generate_report)
    assert "evidence_plain_language" in src
