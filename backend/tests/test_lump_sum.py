"""SA lump-sum tax tests (retirement / severance / withdrawal, cumulative)."""
import pytest
from services import lump_sum as ls


def test_retirement_table():
    assert ls.retirement_lump_sum_tax(550_000) == pytest.approx(0.0)        # tax-free portion
    assert ls.retirement_lump_sum_tax(600_000) == pytest.approx(9_000.0)    # 18% of 50,000
    assert ls.retirement_lump_sum_tax(1_000_000) == pytest.approx(101_700.0)  # 39,600 + 27% of 230,000
    assert ls.retirement_lump_sum_tax(2_000_000) == pytest.approx(447_750.0)  # 143,550 + 36% of 845,000


def test_severance_uses_retirement_table():
    assert ls.severance_benefit_tax(600_000) == ls.retirement_lump_sum_tax(600_000)


def test_withdrawal_table():
    assert ls.withdrawal_lump_sum_tax(27_500) == pytest.approx(0.0)
    assert ls.withdrawal_lump_sum_tax(100_000) == pytest.approx(13_050.0)   # 18% of 72,500


def test_cumulative_basis():
    # a R500k lump after a prior R550k: pushed into the 18% band
    # table(1,050,000) - table(550,000) = (39,600 + 27%*280,000) - 0 = 115,200
    assert ls.retirement_lump_sum_tax(500_000, prior_lump_sums=550_000) == pytest.approx(115_200.0)


def test_assess_structure():
    r = ls.assess_lump_sum(600_000, kind="retirement")
    assert r["tax"] == pytest.approx(9_000.0)
    assert r["net"] == pytest.approx(591_000.0)
    assert r["effective_rate_pct"] == pytest.approx(1.5)


def test_robust_to_none():
    assert ls.retirement_lump_sum_tax(None) == 0.0
    assert ls.assess_lump_sum(None)["tax"] == 0.0
