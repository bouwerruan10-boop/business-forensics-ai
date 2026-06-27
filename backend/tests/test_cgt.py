"""SA Capital Gains Tax (8th Schedule) tests."""
import pytest
from services import cgt
from services.income_tax import income_tax


def test_individual_taxable_capital_gain():
    # R200,000 gain - R50,000 annual exclusion = R150,000 ; x 40% = R60,000
    assert cgt.taxable_capital_gain(200_000) == pytest.approx(60_000.0)


def test_company_no_annual_exclusion():
    # company: no annual exclusion ; R200,000 x 80% = R160,000 ; x 27% = R43,200
    r = cgt.assess_cgt(200_000, taxpayer="company")
    assert r["taxable_capital_gain"] == pytest.approx(160_000.0)
    assert r["cgt_payable"] == pytest.approx(43_200.0)


def test_primary_residence_exclusion():
    # PR gain R3.5m -> first R3m excluded -> R500k ; - R50k annual = R450k ; x40% = R180k
    assert cgt.taxable_capital_gain(3_500_000, primary_residence_gain=3_500_000) == pytest.approx(180_000.0)


def test_capital_loss_carries_no_tax():
    r = cgt.assess_cgt(30_000, total_losses=100_000)
    assert r["aggregate_capital_gain"] == pytest.approx(-70_000.0)
    assert r["net_capital_gain"] == 0.0
    assert r["taxable_capital_gain"] == 0.0
    assert r["cgt_payable"] == 0.0


def test_individual_marginal_incremental():
    # taxed at marginal: tax(other+TCG) - tax(other)
    r = cgt.assess_cgt(200_000, other_taxable_income=500_000, age=30)
    tcg = r["taxable_capital_gain"]          # 60,000
    expected = income_tax(500_000 + tcg, 30) - income_tax(500_000, 30)
    assert r["cgt_payable"] == pytest.approx(round(expected, 2))
    assert r["effective_rate_pct"] > 0


def test_trust_rate():
    r = cgt.assess_cgt(200_000, taxpayer="trust")
    assert r["inclusion_rate"] == 0.80
    assert r["cgt_payable"] == pytest.approx(200_000 * 0.80 * 0.45)


def test_robust_to_none():
    r = cgt.assess_cgt(None)
    assert r["cgt_payable"] == 0.0
    assert r["effective_rate_pct"] == 0.0
