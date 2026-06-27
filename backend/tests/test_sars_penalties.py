"""SARS penalty + interest engine tests (s211 / s223 / interest / exposure band)."""
import pytest
from services import sars_penalties as sp


def test_admin_penalty_brackets():
    assert sp.admin_penalty(200_000)["monthly"] == 250       # <= R250k
    assert sp.admin_penalty(750_000)["monthly"] == 1_000      # R500k-R1m
    assert sp.admin_penalty(20_000_000)["monthly"] == 8_000   # R10m-R50m
    assert sp.admin_penalty(60_000_000)["monthly"] == 16_000  # > R50m
    assert sp.admin_penalty(-50_000)["monthly"] == 250        # assessed loss -> lowest


def test_admin_penalty_caps_at_35_months():
    r = sp.admin_penalty(200_000, months_outstanding=50)
    assert r["months"] == 35
    assert r["total"] == 250 * 35


def test_understatement_penalty_table():
    # gross negligence, standard = 100% of the shortfall
    assert sp.understatement_penalty(100_000, "gross_negligence")["penalty"] == pytest.approx(100_000.0)
    # substantial understatement, obstructive/repeat = 20%
    assert sp.understatement_penalty(100_000, "substantial_understatement", "repeat")["penalty"] == pytest.approx(20_000.0)
    # intentional evasion, repeat = 200%
    assert sp.understatement_penalty(100_000, "intentional_tax_evasion", "repeat")["penalty"] == pytest.approx(200_000.0)
    # voluntary disclosure before notification often 0%
    assert sp.understatement_penalty(100_000, "reasonable_care_not_taken", "vd_before")["penalty"] == 0.0


def test_usp_exposure_band():
    e = sp.usp_exposure(100_000, "high")
    assert e["low_percentage"] == 50 and e["high_percentage"] == 100
    assert e["low_penalty"] == pytest.approx(50_000.0)
    assert e["high_penalty"] == pytest.approx(100_000.0)
    assert "RANGE" in e["note"]
    # unknown level defaults to low
    assert sp.usp_exposure(100_000, "bogus")["risk_level"] == "low"


def test_interest_on_tax():
    # R100,000 at 10.5% for 365 days = R10,500
    assert sp.interest_on_tax(100_000, 365, 10.5) == pytest.approx(10_500.0)
    assert sp.interest_on_tax(100_000, 0) == 0.0


def test_late_payment_penalty():
    assert sp.late_payment_penalty(50_000) == pytest.approx(5_000.0)   # default 10%


def test_robust_to_none():
    assert sp.admin_penalty(None)["monthly"] == 250
    assert sp.understatement_penalty(None)["penalty"] == 0.0
    assert sp.interest_on_tax(None, None) == 0.0
