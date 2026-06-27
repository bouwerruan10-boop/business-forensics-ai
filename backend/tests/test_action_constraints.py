"""Changeable-vs-fixed action-constraints tests (deterministic)."""
from services.action_constraints import annotate


def _report():
    return {
        "financial_ratios": {
            "gross_margin": {"label": "Gross margin", "value": 18.0, "benchmark": 25.0,
                             "unit": "%", "status": "critical"},
            "debtor_days": {"label": "Debtor days", "value": 70.0, "benchmark": 45.0,
                            "unit": "days", "status": "critical"},
        },
        "financial_figures": {"revenue": 5_000_000, "gross_profit": 900_000, "operating_profit": 300_000},
        "currency": "ZAR",
    }


def test_annotates_actions_with_dos_donts_and_ceiling():
    r = annotate(_report())
    by_id = {a["id"]: a for a in r["actions"]}
    assert "gross_margin" in by_id and "debtor_days" in by_id
    gm = by_id["gross_margin"]
    assert gm["dos"] and gm["donts"] and gm["fixed"] and gm["timeline"]
    # realistic ceiling = max gap * close fraction (0.35 for gross_margin)
    assert gm["changeable_fraction"] == 0.35
    assert gm["realistic_ceiling"] == round(gm["max"] * 0.35, 1)
    # the Score is explicitly untouched
    assert "does not change the Imara Score" in r["note"]


def test_always_available_actions_get_default_profile():
    r = annotate(_report())
    by_id = {a["id"]: a for a in r["actions"]}
    # revenue_growth + price are always appended; they have profiles too
    assert "revenue_growth" in by_id
    assert by_id["revenue_growth"]["dos"]


def test_robust_to_garbage():
    # garbage input must not crash; derive_actions still yields the universal levers
    base = annotate({})["count"]            # revenue_growth + price always present
    assert annotate(None)["count"] == base
    assert annotate("nope")["count"] == base
    assert "Imara Score" in annotate(None)["note"]
