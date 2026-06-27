"""SARS audit-risk score tests (aggregates tax_risk_flags into 0-100)."""
from services.audit_risk import build_audit_risk as build


def _report(flags):
    return {"tax_risk_flags": {"available": True, "as_of": "2026/27", "flags": flags}}


def test_no_flags_is_low():
    r = build(_report([]))
    assert r["available"] is True
    assert r["score"] == 0 and r["band"] == "low"


def test_single_medium_is_moderate():
    r = build(_report([{"severity": "medium", "title": "Related party", "code": "rp"}]))
    assert r["score"] == 14 and r["band"] == "moderate"


def test_two_high_is_elevated():
    r = build(_report([{"severity": "high", "title": "Offshore"},
                       {"severity": "high", "title": "Inflow gap"}]))
    assert r["score"] == 56 and r["band"] == "elevated"


def test_score_caps_at_100_and_orders_drivers():
    r = build(_report([{"severity": "high", "title": "a"}] * 5))   # 140 -> capped
    assert r["score"] == 100 and r["band"] == "high"
    assert r["drivers"][0]["points"] >= r["drivers"][-1]["points"]


def test_accepts_flags_dict_directly():
    r = build({"available": True, "flags": [{"severity": "low", "title": "loss"}]})
    assert r["score"] == 6 and r["band"] == "low"


def test_unavailable_and_hostile():
    assert build({"tax_risk_flags": {"available": False}})["available"] is False
    assert build("x")["available"] is False
    assert build({})["available"] is False
