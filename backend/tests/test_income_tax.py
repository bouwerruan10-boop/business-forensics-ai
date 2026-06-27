"""SA individual income-tax tests (2026/27 brackets + rebates + travel + medical)."""
import pytest
from services import income_tax as it


def test_threshold_under_65_is_tax_free():
    # tax threshold = primary rebate / 18% = 17820/0.18 = R99,000
    assert it.income_tax(99_000, age=30) == pytest.approx(0.0)
    assert it.income_tax(99_001, age=30) > 0


def test_bracket_worked_examples():
    # R300,000: 245100*18% + 54900*26% = 44118 + 14274 = 58392; less rebate 17820
    assert it.income_tax(300_000, age=30) == pytest.approx(40_572.0)
    # R500,000: 44118 + 138000*26% + 116900*31% = 116237; less 17820
    assert it.income_tax(500_000, age=30) == pytest.approx(98_417.0)


def test_age_rebates_reduce_tax():
    base = it.income_tax(300_000, age=30)
    over65 = it.income_tax(300_000, age=66)
    over75 = it.income_tax(300_000, age=80)
    assert over65 == pytest.approx(base - 9_765.0)
    assert over75 == pytest.approx(base - 9_765.0 - 3_249.0)


def test_travel_helpers():
    assert it.travel_paye_inclusion(100_000) == pytest.approx(80_000.0)
    assert it.travel_paye_inclusion(100_000, business_use_ge_80pct=True) == pytest.approx(20_000.0)
    assert it.travel_deduction(10_000) == pytest.approx(49_500.0)   # 10000km * R4.95


def test_medical_credit():
    # main+1 dependant = 2 * R376 *12 ; +1 more = + R254*12
    assert it.medical_tax_credit(2) == pytest.approx(376 * 2 * 12)
    assert it.medical_tax_credit(3) == pytest.approx((376 * 2 + 254) * 12)
    assert it.medical_tax_credit(0) == 0.0


def test_assess_refund_and_owing():
    # PAYE overpaid -> refund
    r = it.assess(salary=300_000, paye_paid=50_000, age=30)
    assert r["taxable_income"] == pytest.approx(300_000.0)
    assert r["tax_payable"] == pytest.approx(40_572.0)
    assert r["position"] == "refund"
    assert r["balance"] == pytest.approx(40_572.0 - 50_000.0)
    # retirement + travel deductions reduce taxable income
    r2 = it.assess(salary=300_000, travel_allowance=60_000, travel_business_km=10_000,
                   retirement_contribution=20_000, age=30)
    assert r2["travel_deduction"] == pytest.approx(49_500.0)
    assert r2["retirement_deduction"] == pytest.approx(20_000.0)
    assert r2["taxable_income"] == pytest.approx(300_000 + 60_000 - 49_500 - 20_000)


def test_robust_to_none():
    r = it.assess(salary=None, paye_paid="oops", age=None)
    assert r["taxable_income"] == 0.0
    assert r["position"] == "settled"
