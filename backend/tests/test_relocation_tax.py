"""Tests for the 'Tax Me If You Can' relocation/tax first-pass engine (services/relocation_tax.py).

Covers the deterministic fit logic, the non-negotiable guardrails, adversarial/hostile input,
and that the public /api/tax/relocation endpoint is NOT behind the operator gate.
"""
from services.relocation_tax import relocation_first_pass, DESTINATIONS, GUARDRAILS, AS_OF


def _codes(r):
    return [d["code"] for d in r["destinations"]]


def test_structure_and_disclaimers():
    r = relocation_first_pass({"income_types": ["employment"]})
    assert r["available"] is True
    assert r["as_of"] == AS_OF
    assert r["classification"].startswith("decision-support")
    # never claims to be advice; always routes to a licensed advisor
    assert "advice" in r["is_not"]
    assert "licensed" in r["disclaimer"].lower()
    assert "evasion" in r["disclaimer"].lower()
    assert len(r["destinations"]) == len(DESTINATIONS)


def test_guardrails_present():
    r = relocation_first_pass({})
    titles = " ".join(g["title"] + " " + g["detail"] for g in r["guardrails"]).lower()
    # the compliance moat must always be surfaced
    for needle in ("exit", "substance", "crs", "dac6", "licensed"):
        assert needle in titles, needle
    assert len(GUARDRAILS) >= 5


def test_fit_passive_income_favours_cyprus():
    r = relocation_first_pass({"income_types": ["dividends", "interest", "rental"]})
    assert r["destinations"][0]["code"] == "CY"          # ranked first
    assert r["destinations"][0]["fit"]["level"] == "strong"


def test_fit_employment_favours_uae():
    r = relocation_first_pass({"income_types": ["employment"]})
    ae = next(d for d in r["destinations"] if d["code"] == "AE")
    assert ae["fit"]["level"] == "strong"


def test_portugal_pension_is_weak_and_flagged():
    r = relocation_first_pass({"income_types": ["pension"]})
    pt = next(d for d in r["destinations"] if d["code"] == "PT")
    assert pt["fit"]["level"] == "weak"
    assert "exclud" in pt["income_treatment"]["pension"].lower()  # pensions excluded under IFICI


def test_origin_sa_exit_charge_surfaced():
    r = relocation_first_pass({"origin": "ZA", "income_types": ["capital_gains"]})
    assert "Section 9H" in r["origin_exit"]["exit_charge"]
    assert r["origin_exit"]["code"] == "ZA"


def test_unknown_origin_gets_safe_note():
    r = relocation_first_pass({"origin": "GB"})
    assert r["origin_exit"]["code"] == "GB"
    assert "confirm" in r["origin_exit"]["exit_charge"].lower()


def test_adversarial_inputs_never_crash():
    for bad in [None, {}, [], "nonsense", 42,
                {"income_types": None}, {"income_types": "dividends"},
                {"income_types": ["junk", 5, None, "EMPLOYMENT "]},
                {"destinations": ["XX", "zz"]}, {"destinations": "CY"},
                {"income_types": ["pension"], "destinations": []},
                {"origin": 123, "income_types": {}}]:
        r = relocation_first_pass(bad)
        assert r["available"] is True
        assert isinstance(r["destinations"], list) and len(r["destinations"]) >= 1
        assert len(r["guardrails"]) >= 5


def test_string_income_type_coerced():
    r = relocation_first_pass({"income_types": "EMPLOYMENT "})
    assert "employment" in r["income_types_considered"]


def test_endpoint_is_public_even_with_auth_enabled(monkeypatch):
    import config
    monkeypatch.setattr(config, "AUTH_ENABLED", True)
    from fastapi.testclient import TestClient
    import main
    with TestClient(main.app) as c:
        resp = c.post("/api/tax/relocation", json={"income_types": ["dividends"]})
        assert resp.status_code == 200, resp.status_code     # NOT behind the operator gate
        data = resp.json()
        assert data["available"] is True and data["destinations"]
        # malformed / empty body still returns a valid default
        resp2 = c.post("/api/tax/relocation", content=b"not json")
        assert resp2.status_code == 200
