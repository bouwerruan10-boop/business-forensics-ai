"""NCA / Reg 23A-shaped affordability assessment (deterministic, decision-support)."""
from services.affordability import assess_affordability, affordability_stamp


def test_basic_capacity_from_adjusted_ebitda():
    a = assess_affordability(
        {"interest": 100_000, "total_debt": 1_000_000, "operating_profit": 800_000},
        {"adjusted_ebitda_low": 1_200_000})
    assert a["available"] is True
    assert a["income_available_for_debt_service"] == 1_200_000   # prefers adjusted EBITDA
    assert a["income_source"] == "adjusted_ebitda_low"
    # existing service = finance costs 100k + indicative principal (1,000,000 / 5 = 200,000) = 300,000
    assert a["existing_obligations"]["existing_annual_debt_service"] == 300_000
    assert a["discretionary_surplus_for_new_debt"] == 900_000
    cap = a["new_debt_capacity"]
    # prudent: income/1.5 = 800,000 total allowed; minus 300,000 existing = 500,000 new service
    assert cap["serviceable"] is True
    assert cap["max_new_annual_debt_service_prudent"] == 500_000
    assert cap["implied_new_principal_prudent"] > 0


def test_income_source_fallback_chain():
    assert assess_affordability({"ebitda": 500_000}, {})["income_source"] == "ebitda"
    assert assess_affordability({"operating_profit": 300_000}, {})["income_source"] == "operating_profit"
    # adjusted EBITDA wins when present
    assert assess_affordability({"ebitda": 500_000}, {"adjusted_ebitda_low": 600_000})["income_source"] == "adjusted_ebitda_low"


def test_no_income_measure_is_honest():
    a = assess_affordability({"total_debt": 500_000}, {})
    assert a["available"] is False and "reason" in a
    assert "new_debt_capacity" not in a


def test_non_positive_income_no_capacity():
    a = assess_affordability({"operating_profit": -50_000}, {})
    assert a["available"] is True
    assert a["new_debt_capacity"]["serviceable"] is False


def test_proposed_instalment_verdict_bands():
    figs = {"interest": 0, "operating_profit": 1_500_000}   # income 1.5m, no existing service
    afford = assess_affordability(figs, {}, proposed_annual_instalment=900_000)   # dscr=1.67 >=1.5
    assert afford["proposed_instalment_assessment"]["verdict"] == "affordable"
    marg = assess_affordability(figs, {}, proposed_annual_instalment=1_100_000)   # dscr=1.36 in [1.25,1.5)
    assert marg["proposed_instalment_assessment"]["verdict"] == "marginal"
    un = assess_affordability(figs, {}, proposed_annual_instalment=1_400_000)     # dscr=1.07 <1.25
    assert un["proposed_instalment_assessment"]["verdict"] == "unaffordable"


def test_hostile_and_none_safe():
    for bad in (None, "x", 123, [], {"interest": "junk", "total_debt": float("inf"), "operating_profit": "bad"}):
        a = assess_affordability(bad, bad)
        assert isinstance(a, dict) and "available" in a
    # finite-guard: inf debt stock must not leak into the record
    a = assess_affordability({"operating_profit": 500_000, "total_debt": float("inf")}, {})
    assert a["existing_obligations"]["debt_stock"] is None


def test_stamp_is_compact_and_json_safe():
    a = assess_affordability({"interest": 100_000, "total_debt": 1_000_000, "operating_profit": 800_000},
                             {"adjusted_ebitda_low": 1_200_000}, proposed_annual_instalment=400_000)
    s = affordability_stamp(a)
    assert s["available"] is True and s["income_available_for_debt_service"] == 1_200_000
    assert s["proposed_verdict"] in ("affordable", "marginal", "unaffordable")
    assert affordability_stamp(None)["available"] is False   # hostile-safe
