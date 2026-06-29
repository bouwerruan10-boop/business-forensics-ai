"""PSI population-drift + realised-vs-predicted + the shadow-mode outcome flag (E5/C1)."""
from services.validation import psi, realised_vs_predicted


def test_psi_zero_on_identical_distributions():
    scores = [10, 20, 40, 55, 70, 90] * 10   # 60 scores spread across bands
    r = psi(scores, list(scores))
    assert r["available"] and r["psi"] == 0.0 and r["interpretation"] == "stable"


def test_psi_rises_on_shift():
    baseline = [85] * 30 + [40] * 30          # half high, half mid
    recent = [40] * 55 + [85] * 5             # shifted down
    r = psi(baseline, recent)
    assert r["available"] and r["psi"] > 0.25 and r["interpretation"] == "significant_shift"


def test_psi_insufficient_data_is_honest():
    r = psi([50, 60], [55, 65])
    assert r["available"] is False and "Need >=" in r["reason"]


def test_psi_hostile_safe():
    for bad in (None, "x", [None, "a", float("inf")]):
        assert isinstance(psi(bad, bad), dict)


def test_realised_vs_predicted_monotonic():
    # high scores rarely default, low scores often -> realised bad-rate falls with band
    pairs = ([{"imara_score": 85, "label": 0}] * 15 + [{"imara_score": 85, "label": 1}] * 1
             + [{"imara_score": 30, "label": 1}] * 12 + [{"imara_score": 30, "label": 0}] * 4)
    r = realised_vs_predicted(pairs)
    assert r["available"] and len(r["bands"]) >= 2
    by = {b["band"]: b["realised_bad_rate"] for b in r["bands"]}
    assert min(by.values()) < max(by.values())   # discriminates


def test_realised_vs_predicted_insufficient():
    assert realised_vs_predicted([{"imara_score": 50, "label": 1}])["available"] is False


def test_shadow_flag_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("BF_DB_PATH", str(tmp_path / "shadow.db"))
    import importlib
    import services.database as db
    importlib.reload(db)
    db.init_db()
    # seed an analysis so the FK-ish join works for outcomes_with_scores (not needed for list)
    db.create_analysis("a1", {"company_name": "X"})
    db.record_outcome("a1", "funded", label=0, shadow=True)
    db.record_outcome("a1", "funded", label=1, shadow=False)
    rows = db.list_outcomes()
    shadows = sorted(r["shadow"] for r in rows)
    assert shadows == [0, 1]
    importlib.reload(db)   # restore module state for other tests
