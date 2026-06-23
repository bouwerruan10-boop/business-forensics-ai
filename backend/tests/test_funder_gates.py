"""Funder gates — unit + adversarial pressure tests (v1.71)."""
import json
import math

from services.funder_gates import evaluate_funder_gates

_FIT = {"good", "possible", "unlikely", "ineligible"}


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
    r = evaluate_funder_gates({"industry": "Retail", "entity_type": "Pty Ltd",
                               "cipc_number": "2016/1/07", "annual_revenue": 24_500_000})
    assert r["available"] is True
    keys = {f["key"] for f in r["funders"]}
    assert {"sedfa", "idc", "nef", "business_partners"} <= keys
    for f in r["funders"]:
        assert f["fit"] in _FIT
        assert f["name"] and f["ticket_range"] and f["source"]
        assert isinstance(f["checks"], list) and f["checks"]
    assert "credit decision" in r["is_not"]
    assert "not a recommendation" in r["disclaimer"].lower()
    assert r["data_gaps"]
    json.dumps(r)


def test_idc_only_fits_industrial_above_1m():
    retail = next(f for f in evaluate_funder_gates({"industry": "Retail", "annual_revenue": 24_000_000})["funders"] if f["key"] == "idc")
    assert retail["fit"] == "unlikely"
    mfg = next(f for f in evaluate_funder_gates({"industry": "Manufacturing", "entity_type": "Pty Ltd", "cipc_number": "x", "annual_revenue": 8_000_000})["funders"] if f["key"] == "idc")
    assert mfg["fit"] == "possible"
    # below R1m floor -> unlikely even if industrial
    small = next(f for f in evaluate_funder_gates({"industry": "Manufacturing", "annual_revenue": 400_000})["funders"] if f["key"] == "idc")
    assert small["fit"] == "unlikely"


def test_business_partners_excludes_npo():
    r = evaluate_funder_gates({"industry": "Community services", "entity_type": "NPC", "annual_revenue": 2_000_000})
    bp = next(f for f in r["funders"] if f["key"] == "business_partners")
    assert bp["fit"] == "ineligible"


def test_nef_ownership_gate_and_npo():
    # NPO -> NEF unlikely
    npo = next(f for f in evaluate_funder_gates({"entity_type": "NPC"})["funders"] if f["key"] == "nef")
    assert npo["fit"] == "unlikely"
    # ordinary firm -> possible, with the ownership gate surfaced as the key check
    nef = next(f for f in evaluate_funder_gates({"entity_type": "Pty Ltd", "annual_revenue": 5_000_000})["funders"] if f["key"] == "nef")
    assert nef["fit"] == "possible"
    assert any("black ownership" in c["gate"].lower() for c in nef["checks"])


def test_sedfa_always_a_candidate():
    for rep in [{"annual_revenue": 300_000}, {"annual_revenue": 9_000_000, "cipc_number": "x", "entity_type": "Pty Ltd"}]:
        s = next(f for f in evaluate_funder_gates(rep)["funders"] if f["key"] == "sedfa")
        assert s["fit"] in ("good", "possible")


def test_primary_excludes_unlikely_and_ineligible():
    r = evaluate_funder_gates({"industry": "Retail", "entity_type": "NPC", "annual_revenue": 2_000_000})
    names_unfit = {f["name"] for f in r["funders"] if f["fit"] in ("unlikely", "ineligible")}
    assert all(n not in r["primary"] for n in names_unfit)


def test_adversarial_never_crashes_and_json_safe():
    hostile = [
        None, "x", 123, [], {"annual_revenue": "abc"}, {"annual_revenue": -50},
        {"annual_revenue": float("nan")}, {"annual_revenue": float("inf")},
        {"industry": ["x"]}, {"entity_type": 999, "cipc_number": None},
        {"financial_figures": "wrong"}, {"bbbee_level": {"x": 1}},
        {"industry": "Pty\x00 mining 😀", "annual_revenue": 1e18},
        {"years_in_business": "<1 year"}, {"years_in_business": "3-7 years"},
    ]
    for rep in hostile:
        out = evaluate_funder_gates(rep, rep if isinstance(rep, dict) else None)
        assert isinstance(out, dict) and "available" in out
        if out.get("available"):
            assert len(out["funders"]) == 4
            _json_safe(out)
            json.dumps(out)
