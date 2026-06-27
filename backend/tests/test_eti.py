"""ETI quantification tests against the SARS bands effective 1 April 2025."""
import pytest
from services import eti


def test_band1_percentage():
    assert eti.monthly_eti(2000, 1) == pytest.approx(1200.0)   # 60% of 2000
    assert eti.monthly_eti(2000, 2) == pytest.approx(600.0)    # 30% of 2000


def test_band2_flat():
    assert eti.monthly_eti(3000, 1) == pytest.approx(1500.0)
    assert eti.monthly_eti(3000, 2) == pytest.approx(750.0)
    # boundaries are continuous: at R2,500 the % band and flat band agree
    assert eti.monthly_eti(2500, 1) == pytest.approx(1500.0)


def test_band3_taper():
    assert eti.monthly_eti(6000, 1) == pytest.approx(1125.0)   # 1500 - 75%*500
    assert eti.monthly_eti(6000, 2) == pytest.approx(562.5)    # 750 - 37.5%*500
    assert eti.monthly_eti(7000, 1) == pytest.approx(375.0)    # 1500 - 75%*1500
    # continuous at R5,500 boundary
    assert eti.monthly_eti(5500, 1) == pytest.approx(1500.0)


def test_ceiling_and_zero():
    assert eti.monthly_eti(7500, 1) == 0.0
    assert eti.monthly_eti(9000, 1) == 0.0
    assert eti.monthly_eti(0, 1) == 0.0
    assert eti.monthly_eti(-100, 1) == 0.0


def test_quantify_roster():
    employees = [
        {"age": 25, "monthly_remuneration": 3000},   # qualifies -> 1500
        {"age": 35, "monthly_remuneration": 3000},   # too old -> 0
        {"age": 20, "monthly_remuneration": 8000},   # earns too much -> 0
        {"age": 19, "remuneration": 2000},           # qualifies -> 1200 (60%)
    ]
    r = eti.quantify_eti(employees, year=1)
    assert r["qualifying_count"] == 2
    assert r["monthly_total"] == pytest.approx(2700.0)        # 1500 + 1200
    assert r["annual_projection"] == pytest.approx(32400.0)   # *12
    assert r["employees"][1]["reason"].startswith("not eligible: age")
    assert r["employees"][2]["reason"].startswith("not eligible: earns")


def test_robust_to_missing_and_garbage():
    r = eti.quantify_eti([{"age": "oops"}, {}, None and {}], year=1)
    assert r["qualifying_count"] == 0
    assert r["monthly_total"] == 0.0


def test_max_constants_corrected():
    from services import sa_rates
    assert sa_rates.ETI_MAX_MONTHLY_Y1 == 1500.0   # was wrongly 2500
    assert sa_rates.ETI_MAX_MONTHLY_Y2 == 750.0     # was wrongly 1250
