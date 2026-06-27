"""SA provisional-tax (IRP6) tests: payments, basic amount, par-20 penalty."""
import pytest
from services import provisional_tax as pt
from services.income_tax import income_tax


def test_basic_amount_escalation():
    assert pt.basic_amount(500_000) == pytest.approx(500_000.0)
    assert pt.basic_amount(500_000, escalation_years=2) == pytest.approx(500_000 * 1.08 ** 2)


def test_payments():
    # income_tax(300000, 30) = 40,572 -> first = half = 20,286
    assert pt.first_payment(300_000, age=30) == pytest.approx(20_286.0)
    assert pt.second_payment(300_000, age=30, first_paid=20_286) == pytest.approx(20_286.0)
    # PAYE reduces the second payment
    assert pt.second_payment(300_000, age=30, paye_paid=10_000, first_paid=15_286) == pytest.approx(15_286.0)


def test_penalty_over_1m():
    # actual 2,000,000 (>R1m) -> safe harbour = tax on 80% = tax(1,600,000) = 534,293
    # tax paid = tax(1,000,000) = 288,293 ; penalty = 20% * (534,293 - 288,293) = 49,200
    paid = income_tax(1_000_000, 0)
    pen = pt.underestimation_penalty(2_000_000, 1_000_000, age=0, tax_already_paid=paid)
    assert pen == pytest.approx(49_200.0)
    # paying at/above the safe harbour -> no penalty
    assert pt.underestimation_penalty(2_000_000, 1_600_000, age=0, tax_already_paid=600_000) == 0.0


def test_penalty_le_1m_uses_lesser_of_90pct_or_basic():
    # actual 800,000 ; basic 400,000 ; 90% of actual = 720,000 -> required = min = 400,000
    # required tax = tax(400,000) = 67,417 ; paid = tax(300,000) = 40,572 -> 20%*(26,845) = 5,369
    paid = income_tax(300_000, 0)
    pen = pt.underestimation_penalty(800_000, 300_000, age=0, basic_amt=400_000, tax_already_paid=paid)
    assert pen == pytest.approx(5_369.0)
    # estimate that already covers the basic amount -> no penalty
    assert pt.underestimation_penalty(800_000, 400_000, age=0, basic_amt=400_000,
                                      tax_already_paid=income_tax(400_000, 0)) == 0.0


def test_assess_provisional_integration():
    r = pt.assess_provisional(300_000, age=30, latest_assessed_taxable=280_000, actual_taxable=300_000)
    assert r["tax_on_estimate"] == pytest.approx(40_572.0)
    assert r["total_provisional"] == pytest.approx(40_572.0)   # p1 + p2 = full tax (no PAYE)
    assert r["full_year_tax"] == pytest.approx(40_572.0)
    assert r["underestimation_penalty"] == 0.0                 # estimate == actual
    assert r["balance_on_assessment"] == pytest.approx(0.0)


def test_robust_to_none():
    r = pt.assess_provisional(None, age=None)
    assert r["tax_on_estimate"] == 0.0
    assert r["total_provisional"] == 0.0
