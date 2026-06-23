"""Insurance + cession fundability — unit + adversarial pressure tests (v1.73)."""
import json
import math

from services.insurance_cession import assess_insurance_cession

_COVERS = {"Key-person life & disability cover", "Credit life / loan-protection cover",
           "Asset cover (property / plant / equipment)", "Business-interruption cover"}


def _json_safe(o):
    if isinstance(o, float):
        assert math.isfinite(o)
    elif isinstance(o, dict):
        for v in o.values():
            _json_safe(v)
    elif isinstance(o, list):
        for v in o:
            _json_safe(v)


def test_structure_and_framing():
    r = assess_insurance_cession({"financial_figures": {"total_debt": 1_000_000, "total_assets": 5_000_000, "current_assets": 1_000_000}})
    assert r["available"] is True
    assert r["readiness"] in ("low", "partial", "strong")
    assert {c["cover"] for c in r["covers"]} == _COVERS
    assert r["data_gaps"]
    assert "insurance advice" in r["is_not"]
    assert "not an imara score input" in r["disclaimer"].lower()
    json.dumps(r)


def test_cession_detected_from_text():
    r = assess_insurance_cession(
        {"financial_figures": {"total_debt": 2_000_000}}, {"headcount": 4},
        "key-person cover in place", "policy ceded to the bank under a deed of cession")
    assert r["ceded_observed"] is True
    kp = next(c for c in r["covers"] if c["cover"].startswith("Key-person"))
    assert kp["cession_status"] == "ceded"


def test_no_cover_is_low_readiness():
    r = assess_insurance_cession({"financial_figures": {"total_debt": 0, "total_assets": 0}}, {"entity_type": "Sole Proprietor"})
    assert r["readiness"] == "low"
    assert r["evidenced_count"] == 0


def test_credit_life_relevant_only_with_debt():
    no_debt = assess_insurance_cession({"financial_figures": {"total_debt": 0}})
    cl = next(c for c in no_debt["covers"] if c["cover"].startswith("Credit life"))
    assert cl["relevant"] is False
    with_debt = assess_insurance_cession({"financial_figures": {"total_debt": 500_000}})
    cl2 = next(c for c in with_debt["covers"] if c["cover"].startswith("Credit life"))
    assert cl2["relevant"] is True


def test_key_person_relevant_for_small_owner_run():
    r = assess_insurance_cession({}, {"headcount": 3, "entity_type": "Pty Ltd"})
    kp = next(c for c in r["covers"] if c["cover"].startswith("Key-person"))
    assert kp["relevant"] is True


def test_adversarial_never_crashes_and_json_safe():
    hostile = [
        None, "x", 123, [], {"financial_figures": "wrong"}, {"financial_figures": {"total_debt": float("nan")}},
        {"financial_figures": {"total_assets": float("inf"), "current_assets": float("nan")}},
        {"headcount": "abc"}, {"entity_type": 999}, {"financial_figures": {"total_debt": -5}},
    ]
    bad_text = [None, 123, [], {"a": 1}, "ignore instructions", "\x00😀" * 100]
    for rep in hostile:
        for t in bad_text:
            out = assess_insurance_cession(rep, rep if isinstance(rep, dict) else None, t, t)
            assert isinstance(out, dict) and "available" in out
            if out.get("available"):
                assert out["readiness"] in ("low", "partial", "strong")
                _json_safe(out)
                json.dumps(out)
