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


# ── Quantification layer (v1.68) ───────────────────────────────────────────────

def test_quantification_present_with_amounts():
    r = relocation_first_pass({"income": {"employment": 1500000, "dividends": 800000}})
    assert r["quantified"] is True
    assert isinstance(r["indicative_current_sa_tax"], float) and r["indicative_current_sa_tax"] > 0
    assert "estimates_disclaimer" in r
    for d in r["destinations"]:
        assert "indicative_destination_tax" in d
        assert "indicative_annual_saving" in d
        assert "saving_pct" in d


def test_uae_zero_tax_max_saving():
    r = relocation_first_pass({"income": {"employment": 1000000, "dividends": 500000}})
    ae = next(d for d in r["destinations"] if d["code"] == "AE")
    assert ae["indicative_destination_tax"] == 0.0
    assert ae["saving_pct"] == 100.0


def test_amounts_derive_income_set_and_quantify_only_for_za():
    r = relocation_first_pass({"income": {"dividends": 600000}})
    assert "dividends" in r["income_types_considered"]
    # non-ZA origin: corpus lacks local rates -> no quantification
    r2 = relocation_first_pass({"origin": "GB", "income": {"dividends": 600000}})
    assert r2["quantified"] is False
    assert r2["indicative_current_sa_tax"] is None


def test_exit_cgt_estimate():
    r = relocation_first_pass({
        "income": {"employment": 500000},
        "assets": {"worldwide_market_value": 10000000, "base_cost": 4000000},
    })
    est = r["origin_exit"]["exit_cgt_estimate"]
    assert est["deemed_gain"] == 6000000.0
    assert est["indicative_exit_cgt"] == round(6000000.0 * 0.18, 2)


def test_no_amounts_means_no_quantification():
    r = relocation_first_pass({"income_types": ["dividends"]})
    assert r["quantified"] is False
    assert r["indicative_current_sa_tax"] is None
    assert all("indicative_destination_tax" not in d for d in r["destinations"])


def test_quantification_adversarial_never_crashes():
    for bad in [
        {"income": {"employment": "1500000", "dividends": -99, "interest": None, "junk": 9}},
        {"income": {"employment": "abc"}},
        {"income": "not-a-dict"},
        {"income": {}, "assets": "nope"},
        {"income": {"dividends": 1e12}},
        {"income": {"employment": float("nan")}},
        {"assets": {"worldwide_market_value": "5m", "base_cost": None}},
    ]:
        out = relocation_first_pass(bad)
        assert out["available"] is True and "estimates_disclaimer" in out


def test_shared_sa_exit_not_mutated_by_cgt_estimate():
    import services.relocation_tax as rt
    relocation_first_pass({"income": {"employment": 1}, "assets": {"worldwide_market_value": 9, "base_cost": 1}})
    assert "exit_cgt_estimate" not in rt.SA_EXIT


# ── Added corridors: Mauritius + Malta (v1.69) ─────────────────────────────────

def test_mauritius_and_malta_present_and_complete():
    from services.relocation_tax import DESTINATIONS, INCOME_TYPES
    for code in ("MU", "MT"):
        d = DESTINATIONS[code]
        assert d["name"] and d["residency_test"] and d["headline"]
        assert d["gotchas"] and d["sources"]
        # effective_rates must cover every income type (quantification reads them)
        for t in INCOME_TYPES:
            assert t in d["effective_rates"]


def test_new_corridors_appear_in_default_run():
    r = relocation_first_pass({"income_types": ["dividends"]})
    codes = {d["code"] for d in r["destinations"]}
    assert {"MU", "MT"} <= codes


def test_mauritius_malta_strong_for_passive():
    r = relocation_first_pass({"income_types": ["dividends", "rental"]})
    fit = {d["code"]: d["fit"]["level"] for d in r["destinations"]}
    assert fit["MU"] == "strong"
    assert fit["MT"] == "strong"


def test_new_corridors_quantify():
    r = relocation_first_pass({"income": {"employment": 1000000, "dividends": 500000}})
    mu = next(d for d in r["destinations"] if d["code"] == "MU")
    mt = next(d for d in r["destinations"] if d["code"] == "MT")
    # foreign dividends sit at 0%; employment taxed at the corridor's effective rate
    assert mu["indicative_destination_tax"] == round(1000000 * 0.20, 2)
    assert mt["indicative_destination_tax"] == round(1000000 * 0.35, 2)
    assert mu["indicative_annual_saving"] > 0


def test_selecting_only_new_corridors():
    r = relocation_first_pass({"destinations": ["MU", "MT"], "income_types": ["capital_gains"]})
    assert [d["code"] for d in r["destinations"]] == ["MU", "MT"]
    # Mauritius (no CGT) and Malta (foreign CGT untaxed) both keep capital_gains at 0%
    for d in r["destinations"]:
        assert d["income_treatment"].get("capital_gains")


# ── v1.79: full-capability expansion (flat-fee corridors + enrichment + sequencing) ──

def test_eight_corridors_incl_flat_fee():
    from services.relocation_tax import DESTINATIONS
    for c in ("AE", "CY", "PT", "MU", "MT", "GR", "IT", "CH"):
        assert c in DESTINATIONS
    r = relocation_first_pass({"income_types": ["dividends"]})
    codes = {d["code"] for d in r["destinations"]}
    assert {"GR", "IT", "CH"} <= codes


def test_corridor_enrichment_fields_present():
    r = relocation_first_pass({"income_types": ["employment"]})
    for d in r["destinations"]:
        assert d["regime"] in ("rate", "flat_fee")
        assert "investment_route" in d and "substance" in d
        assert d["dta_with_sa"] is True
        if d["regime"] == "flat_fee":
            assert d["flat_fee"]["amount_zar"] and d["flat_fee"]["note"]


def test_flat_fee_strong_for_ultra_high_income():
    r = relocation_first_pass({"income": {"employment": 20_000_000, "dividends": 5_000_000}})
    gr = next(d for d in r["destinations"] if d["code"] == "GR")
    assert gr["regime"] == "flat_fee"
    assert gr["indicative_destination_tax"] == 2_000_000  # the fixed EUR100k fee in ZAR
    assert gr["fit"]["level"] == "strong"  # current SA tax >> the fee
    assert gr["indicative_annual_saving"] > 0


def test_flat_fee_weak_for_modest_income():
    r = relocation_first_pass({"income": {"employment": 900_000}})
    for code in ("GR", "IT", "CH"):
        d = next(x for x in r["destinations"] if x["code"] == code)
        assert d["fit"]["level"] == "weak"  # fixed fee exceeds modest SA tax
        assert d["indicative_annual_saving"] < 0  # it would COST more


def test_sequencing_and_cost_and_cfc_guardrail():
    r = relocation_first_pass({})
    assert isinstance(r["sequencing"], list) and len(r["sequencing"]) >= 6
    assert isinstance(r["cost_considerations"], list) and r["cost_considerations"]
    assert "fx_assumption" in r
    # a CFC guardrail must now exist (6th)
    assert any("CFC" in g["title"] or "company" in g["title"].lower() for g in r["guardrails"])
    assert len(r["guardrails"]) >= 6


def test_flat_fee_corridors_survive_no_amounts_and_adversarial():
    # no amounts -> flat-fee cards still render with the fee + a generic fit, no crash
    r = relocation_first_pass({"destinations": ["GR", "IT", "CH"], "income_types": ["pension"]})
    assert len(r["destinations"]) == 3
    for d in r["destinations"]:
        assert d["flat_fee"]["amount_zar"] > 0
    for bad in [None, {"income": "x"}, {"income": {"employment": float("nan")}}, {"destinations": ["GR", "ZZ"]}]:
        out = relocation_first_pass(bad)
        assert out["available"] and out["destinations"]


# ── v1.80: stay-and-optimise legal tax-efficiency levers ───────────────────────

def test_stay_and_optimise_present_and_framed():
    r = relocation_first_pass({"income_types": ["employment"]})
    assert isinstance(r["stay_and_optimise"], list) and r["stay_and_optimise"]
    note = r["stay_and_optimise_note"].lower()
    assert "legal" in note and "not advice" in note and "gaar" in note  # legal-efficiency, not a scheme
    for lv in r["stay_and_optimise"]:
        assert lv["section"] and lv["lever"] and lv["what"] and lv["indicative"]


def test_levers_match_income_mix():
    from services.relocation_tax import stay_and_optimise
    # business profile surfaces the SBC + business-incentive levers
    biz = {l["section"] for l in stay_and_optimise({"business"})}
    assert "s12E" in biz and "s12H / s11D / s12BA" in biz
    # interest profile surfaces the interest exemption; employment surfaces the foreign-employment exemption
    assert any(l["section"] == "s10(1)(i)" for l in stay_and_optimise({"interest"}))
    assert any(l["section"] == "s10(1)(o)(ii)" for l in stay_and_optimise({"employment"}))
    # capital_gains profile does NOT pull the business-only SBC lever
    cg = {l["section"] for l in stay_and_optimise({"capital_gains"})}
    assert "s12E" not in cg


def test_all_levers_when_no_income_specified():
    from services.relocation_tax import stay_and_optimise
    assert len(stay_and_optimise(set())) == 10  # the full corpus


def test_universal_levers_always_appear():
    from services.relocation_tax import stay_and_optimise
    # TFSA, donations and medical credits are "all"-profile levers -> always present
    for prof in ({"interest"}, {"pension"}, {"dividends"}, {"employment"}, set()):
        secs = {l["section"] for l in stay_and_optimise(prof)}
        assert "s12T" in secs and "s18A" in secs and "s6A / s6B" in secs
    # RA applies to earned/most income but NOT to a dividends-only earner
    assert "s11F" in {l["section"] for l in stay_and_optimise({"employment"})}
    assert "s11F" not in {l["section"] for l in stay_and_optimise({"dividends"})}


def test_stay_and_optimise_adversarial():
    from services.relocation_tax import stay_and_optimise
    for bad in [None, "x", 123, [], {"a": 1}, {"employment"}]:
        out = stay_and_optimise(bad)
        assert isinstance(out, list) and out  # never crashes, always returns levers


def test_num_rejects_non_finite_and_output_stays_finite():
    import math, json as _j
    from services.relocation_tax import _num
    assert _num("Infinity") == 0.0 and _num(float("inf")) == 0.0 and _num(float("nan")) == 0.0
    def _finite(o):
        if isinstance(o, float):
            assert math.isfinite(o)
        elif isinstance(o, dict):
            [_finite(v) for v in o.values()]
        elif isinstance(o, list):
            [_finite(v) for v in o]
    for body in ({"assets": {"worldwide_market_value": "Infinity"}}, {"income": {"employment": "Infinity"}}):
        r = relocation_first_pass(body)
        _finite(r); _j.dumps(r)
