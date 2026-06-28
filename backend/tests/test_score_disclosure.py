"""POPIA s71(3) disclosure + contestability tests for the Imara Score."""
import pytest

from services.score_disclosure import build_disclosure, record_contestation, list_contestations

_REPORT = {
    "imara_score": 62, "imara_band": "C", "imara_label": "Developing",
    "imara_confidence": "medium", "imara_completeness": 75,
    "imara_components": [
        {"label": "Profitability", "value": 55, "weight": 0.30},
        {"label": "Credit Readiness", "value": 70, "weight": 0.25},
        {"label": "Risk & Compliance", "value": 40, "weight": 0.20},
        {"label": "Tax Compliance", "value": 80, "weight": 0.25},
    ],
    "financial_ratios": {"net_margin": {"value": 4.2, "benchmark": 8.0}},
}


def test_disclosure_has_underlying_logic_and_rights():
    d = build_disclosure(_REPORT)
    assert d["available"] is True and d["score"] == 62
    # contributions sorted by points added (value*weight); Tax Compliance 80*0.25=20 is top
    top = d["underlying_logic"]["components"][0]
    assert top["factor"] == "Tax Compliance" and top["contribution"] == pytest.approx(20.0)
    # POPIA s71(3): underlying logic + a representation route
    assert d["your_rights"]["underlying_logic_provided"] is True
    assert "make_representations" in d["your_rights"]
    assert d["principal_reasons"]      # NCA s62 dominant reasons present


def test_disclosure_shows_inputs_used_and_absent():
    d = build_disclosure(_REPORT)
    used = {i["factor"]: i["used"] for i in d["inputs_used"]}
    assert used["Profitability"] is True
    assert used["Market Visibility"] is False    # not produced this run -> disclosed as not used
    assert len(d["inputs_used"]) == 8


def test_disclosure_robust():
    assert build_disclosure("x")["available"] is False
    assert build_disclosure({})["available"] is False
    assert build_disclosure({"imara_score": 50})["available"] is False   # no components


def test_contestation_roundtrip_is_immutable(tmp_path, monkeypatch):
    import services.database as db
    monkeypatch.setattr(db, "_DB_PATH", tmp_path / "contest.db")
    db.init_db()

    res = record_contestation("a-1", factor="Profitability",
                              statement="Margins recovered in Q4, not reflected.", contact="ruan@x.co")
    assert res["record_hash"] and res["status"] == "lodged"

    lst = list_contestations("a-1")
    assert lst["count"] == 1
    assert lst["contestations"][0]["factor"] == "Profitability"
    assert lst["contestations"][0]["type"] == "score_contestation"
    # a second analysis's contestations don't leak in
    assert list_contestations("a-2")["count"] == 0
    # the tamper-evident chain still verifies after the append
    assert db.verify_audit_chain()["intact"] is True


def test_contestation_coerces_hostile_input(tmp_path, monkeypatch):
    import services.database as db
    monkeypatch.setattr(db, "_DB_PATH", tmp_path / "contest2.db")
    db.init_db()
    res = record_contestation(None, factor=None, statement=12345, contact={"x": 1})
    assert isinstance(res["statement"], str) and isinstance(res["contact"], str)
