"""SA assessed-loss set-off tests (s20 80%/R1m company cap; s20A ring-fencing)."""
import pytest
from services import assessed_losses as al


def test_company_80pct_cap_bites():
    # TI 5,000,000; loss 6,000,000 -> cap = 80% x 5m = 4m -> 1m stays taxable
    r = al.company_loss_setoff(5_000_000, 6_000_000)
    assert r["cap_applied"] == pytest.approx(4_000_000.0)
    assert r["allowed_setoff"] == pytest.approx(4_000_000.0)
    assert r["taxable_income_after"] == pytest.approx(1_000_000.0)
    assert r["carried_forward"] == pytest.approx(2_000_000.0)
    assert r["capped"] is True


def test_company_r1m_floor_when_income_low():
    # TI 800,000; floor R1m > 80% (640k), but set-off can't exceed income -> nil
    r = al.company_loss_setoff(800_000, 2_000_000)
    assert r["cap_applied"] == pytest.approx(1_000_000.0)
    assert r["allowed_setoff"] == pytest.approx(800_000.0)
    assert r["taxable_income_after"] == pytest.approx(0.0)
    assert r["carried_forward"] == pytest.approx(1_200_000.0)


def test_company_small_loss_full_setoff():
    # loss below the R1m floor and below income -> used in full, nothing capped
    r = al.company_loss_setoff(500_000, 300_000)
    assert r["allowed_setoff"] == pytest.approx(300_000.0)
    assert r["taxable_income_after"] == pytest.approx(200_000.0)
    assert r["carried_forward"] == pytest.approx(0.0)
    assert r["capped"] is False


def test_individual_full_setoff_no_cap():
    r = al.individual_loss_setoff(600_000, 200_000)
    assert r["allowed_setoff"] == pytest.approx(200_000.0)
    assert r["taxable_income_after"] == pytest.approx(400_000.0)
    assert r["ring_fenced"] is False


def test_individual_s20a_ringfence_top_bracket_suspect_trade():
    # above the top-rate threshold + suspect trade -> ring-fenced (no set-off)
    r = al.individual_loss_setoff(2_000_000, 500_000, suspect_trade=True)
    assert r["ring_fenced"] is True
    assert r["allowed_setoff"] == 0.0
    assert r["carried_forward"] == pytest.approx(500_000.0)


def test_individual_suspect_trade_below_threshold_not_ringfenced():
    # suspect trade but income below the top-rate point -> still full set-off
    r = al.individual_loss_setoff(500_000, 300_000, suspect_trade=True)
    assert r["ring_fenced"] is False
    assert r["allowed_setoff"] == pytest.approx(300_000.0)


def test_ring_fence_threshold_is_top_bracket():
    assert al.ring_fence_threshold() == pytest.approx(1_878_600.0)


def test_assess_dispatch_and_robust():
    assert al.assess_assessed_loss(5_000_000, 6_000_000, "company")["taxable_income_after"] == pytest.approx(1_000_000.0)
    assert al.assess_assessed_loss(600_000, 200_000, "individual")["allowed_setoff"] == pytest.approx(200_000.0)
    # hostile / empty
    r = al.assess_assessed_loss(None, None, "bogus")
    assert r["taxpayer"] == "company"
    assert r["allowed_setoff"] == 0.0
