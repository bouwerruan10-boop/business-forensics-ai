"""Disparate-impact / four-fifths-rule fairness monitoring (proxy-based, deterministic)."""
from services.fairness import disparate_impact, fairness_report


def _rows(group_key, spec):
    """spec: {group: (n_favourable, n_total)} -> records with band A (fav) / E (not)."""
    rows = []
    for g, (fav, n) in spec.items():
        for i in range(n):
            rows.append({group_key: g, "imara_band": "A" if i < fav else "E",
                         "imara_score": 80 if i < fav else 30})
    return rows


def test_clean_parity_passes():
    # both groups 50% favourable -> ratio 1.0
    di = disparate_impact(_rows("industry", {"retail": (5, 10), "services": (5, 10)}), "industry")
    assert di["available"] and di["adverse_impact_ratio"] == 1.0 and di["passes_four_fifths_rule"] is True


def test_biased_distribution_flags():
    # retail 80% favourable, services 20% -> ratio 0.25 < 0.8
    di = disparate_impact(_rows("industry", {"retail": (8, 10), "services": (2, 10)}), "industry")
    assert di["adverse_impact_ratio"] == 0.25 and di["passes_four_fifths_rule"] is False
    assert di["mean_score_gap"] is not None and di["mean_score_gap"] > 0


def test_small_group_is_dropped_and_honest():
    di = disparate_impact(_rows("industry", {"retail": (3, 4), "services": (5, 10)}), "industry")
    # retail n=4 < min 5 -> only one qualifying group -> insufficient
    assert di["available"] is False and di["groups_below_min_sample"] == 1


def test_missing_group_key_skipped():
    rows = [{"industry": None, "imara_band": "A", "imara_score": 80}] * 8
    di = disparate_impact(rows, "industry")
    assert di["available"] is False   # no usable groups


def test_favourable_by_score_threshold_when_band_missing():
    rows = ([{"industry": "x", "imara_score": 70}] * 6) + ([{"industry": "y", "imara_score": 30}] * 6)
    di = disparate_impact(rows, "industry", score_threshold=50)
    assert di["available"] and di["adverse_impact_ratio"] == 0.0   # y group 0% favourable


def test_hostile_inputs_safe():
    for bad in (None, "x", 123, [1, 2, {"industry": "a"}]):
        assert isinstance(disparate_impact(bad, "industry"), dict)


def test_fairness_report_over_reports():
    reports = ([{"imara_band": "A", "imara_score": 80, "industry": "retail", "country": "South Africa"}] * 6
               + [{"imara_band": "E", "imara_score": 30, "industry": "mining", "country": "South Africa"}] * 6)
    rep = fairness_report(reports)
    assert rep["available"] and rep["sample_size"] == 12
    assert rep["industry"]["available"] is True
    assert rep["region"]["available"] is False   # single region -> insufficient
