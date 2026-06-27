"""SA physical-presence residency test (s1 'resident')."""
from services.tax_residency import physical_presence_test as t


def test_clearly_resident():
    r = t(200, [200, 200, 200, 200, 200])
    assert r["resident_by_presence"] is True
    assert r["status"] == "resident"
    assert r["aggregate_prior_days"] == 1000


def test_fails_aggregate_915():
    # each prior > 91 but aggregate 500 < 915
    r = t(200, [100, 100, 100, 100, 100])
    assert r["resident_by_presence"] is False
    assert r["status"] == "not_resident_by_presence"


def test_fails_each_year_prong():
    # one prior year only 50 days (<=91)
    r = t(200, [200, 200, 50, 200, 200])
    assert r["resident_by_presence"] is False


def test_fails_current_year():
    r = t(80, [200, 200, 200, 200, 200])
    assert r["resident_by_presence"] is False


def test_cessation_330_days():
    r = t(200, [200, 200, 200, 200, 200], days_continuously_absent=330)
    assert r["ceases_on_absence"] is True
    assert r["status"] == "ceased"


def test_needs_five_prior_years():
    r = t(200, [200, 200, 200, 200])   # only 4
    assert r["resident_by_presence"] is False


def test_robust_to_hostile():
    r = t("x", None)
    assert r["available"] is True
    assert r["status"] == "not_resident_by_presence"
