"""Regression tests for the simulator improvements: realistic magnitudes,
correlated Monte Carlo, and surfaced assumptions."""
import main
from services.simulation import derive_actions, monte_carlo, apply_actions


def test_action_defaults_are_realistic_fraction_of_gap():
    acts = {a["id"]: a for a in derive_actions(main.DEMO_REPORT)}
    gm = acts["gross_margin"]
    assert gm["default"] < gm["max"]                      # not the full benchmark gap
    assert 0.2 * gm["max"] <= gm["default"] <= 0.6 * gm["max"]
    # days-unit action default is a whole number
    assert acts["debtor_days"]["default"] == round(acts["debtor_days"]["default"])


def test_monte_carlo_is_correlated_and_surfaces_assumptions():
    sel = [{"id": a["id"], "intensity": 1.0} for a in derive_actions(main.DEMO_REPORT)[:4]]
    mc = monte_carlo(main.DEMO_REPORT, sel, n=2000)
    npd = mc["net_profit_delta"]
    assert npd["p10"] < npd["p50"] < npd["p90"]           # a real, non-collapsed band
    assert 0.0 <= mc["prob_reach_next_band"] <= 1.0
    a = mc["assumptions"]["monte_carlo"]
    assert "execution_factor" in a and "shared" in a["execution_factor"]   # correlation surfaced
    # deterministic (seeded)
    assert monte_carlo(main.DEMO_REPORT, sel, n=2000)["imara_score"] == mc["imara_score"]


def test_apply_actions_surfaces_assumptions_and_zero_noop():
    r = apply_actions(main.DEMO_REPORT, [])
    assert r["net_profit_delta"] == 0 and r["imara_score_delta"] == 0   # no-op stays zero
    assert "assumptions" in r and r["assumptions"]["company_tax_rate"] == 0.27
    assert "realisation_by_scenario" in r["assumptions"]


def test_simulator_ignores_malformed_action_items():
    """The client supplies the action list; malformed items must not 500 the simulator."""
    rep = main.DEMO_REPORT
    for acts in (["junk"], [{}], [123], [{"id": "nope"}], [{"id": "gross_margin", "intensity": "x"}], "notalist", None):
        r = apply_actions(rep, acts, "expected")
        assert "net_profit_delta" in r
        mc = monte_carlo(rep, acts, n=100)
        assert "net_profit_delta" in mc


def test_simulator_scenario_ordering_and_bounds():
    """optimistic >= expected >= pessimistic impact; projected score stays 0-100."""
    rep = main.DEMO_REPORT
    sel = [{"id": a["id"], "intensity": 1.0} for a in derive_actions(rep)]
    o = apply_actions(rep, sel, "optimistic")
    e = apply_actions(rep, sel, "expected")
    p = apply_actions(rep, sel, "pessimistic")
    assert o["net_profit_delta"] >= e["net_profit_delta"] >= p["net_profit_delta"]
    assert 0 <= o["projected"]["imara_score"] <= 100
