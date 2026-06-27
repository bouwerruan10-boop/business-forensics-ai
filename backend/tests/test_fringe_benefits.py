"""SA fringe-benefit (7th Schedule) tests."""
import pytest
from services import fringe_benefits as fb


def test_company_car():
    # R400,000 determined value x 3.5% x 12 = R168,000
    assert fb.company_car_benefit(400_000) == pytest.approx(168_000.0)
    # with maintenance plan: 3.25%
    assert fb.company_car_benefit(400_000, has_maintenance_plan=True) == pytest.approx(156_000.0)


def test_low_interest_loan():
    # R500,000 loan, 0% paid, official 7.75% -> R38,750
    assert fb.low_interest_loan_benefit(500_000) == pytest.approx(38_750.0)
    # paying 5% -> shortfall 2.75% -> R13,750
    assert fb.low_interest_loan_benefit(500_000, interest_rate_paid_pct=5) == pytest.approx(13_750.0)
    # paying at/above official -> nil
    assert fb.low_interest_loan_benefit(500_000, interest_rate_paid_pct=8) == 0.0


def test_accommodation_formula():
    # (A - 91,250) x 17/100 ; A = 491,250 -> 400,000 x 17% = 68,000
    assert fb.accommodation_benefit(491_250) == pytest.approx(68_000.0)
    # furnished + power -> C = 19
    assert fb.accommodation_benefit(491_250, furnished=True, employer_supplies_power=True) == pytest.approx(76_000.0)
    # not owned -> lower of formula or cost
    assert fb.accommodation_benefit(491_250, cost_to_employer=50_000, employer_owned=False) == pytest.approx(50_000.0)


def test_assess_aggregate():
    r = fb.assess_fringe_benefits(car_determined_value=400_000, loan_amount=500_000)
    assert r["company_car"] == pytest.approx(168_000.0)
    assert r["low_interest_loan"] == pytest.approx(38_750.0)
    assert r["total_taxable_fringe_benefits"] == pytest.approx(206_750.0)
    assert r["official_rate_used"] == 7.75


def test_robust_to_none():
    assert fb.company_car_benefit(None) == 0.0
    r = fb.assess_fringe_benefits()
    assert r["total_taxable_fringe_benefits"] == 0.0
