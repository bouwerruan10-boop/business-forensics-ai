"""Tests for the deterministic derived-metrics (DSCR / EBITDA bridge / procurement WC / PIS)."""
from services.derived_metrics import (
    annual_debt_service, ebitda_bridge_block, dscr_block, procurement_wc_block, pis_block,
)
from memory.shared_memory import SharedMemory


def _mem():
    m = SharedMemory()
    m.business_name = "Acme"; m.industry = "retail"; m.industry_key = "general"
    m.annual_revenue = 12_000_000; m.headcount = 12; m.currency = "ZAR"
    m.financial_figures = {
        "revenue": 12_000_000, "cogs": 8_700_000, "gross_profit": 3_300_000,
        "operating_profit": 300_000, "net_profit": 120_000, "interest": 180_000,
        "receivables": 2_300_000, "inventory": 1_900_000, "current_assets": 4_600_000,
        "current_liabilities": 3_100_000, "payables": 1_400_000, "total_debt": 2_200_000,
        "equity": 1_800_000}
    return m


def test_annual_debt_service_annuity_math():
    # 2.2M at 14.5% over 5y -> ~R648,542 (level annuity)
    ds = annual_debt_service(2_200_000, 0.145, 5)
    assert abs(ds - 648_542) < 50
    assert annual_debt_service(0, 0.1, 5) == 0.0
    assert annual_debt_service(100_000, 0.0, 5) == 20_000.0   # zero-rate -> straight principal


def test_ebitda_bridge_numbers():
    b = ebitda_bridge_block(_mem())
    assert "EBIT margin: 2.5%" in b
    assert "R1,428,000" in b            # 11.9pp x 12M
    assert "R1,236,000" in b            # gross-margin drag


def test_dscr_numbers():
    b = dscr_block(_mem())
    assert "R648,542" in b
    assert "0.46x" in b
    assert "1.67x" in b                 # interest cover EBIT/interest = 300k/180k


def test_procurement_wc_numbers():
    b = procurement_wc_block(_mem())
    assert "R570,000" in b              # 30% of 1.9M inventory holding cost
    assert "R1,065,753" in b            # inventory days cut to benchmark


def test_pis_floor():
    b = pis_block(_mem())
    assert ">= 25" in b                 # 12 headcount + 12 rev-points + 1 shareholder
    assert "compilation suffices" in b  # PIS < 100


def test_blocks_return_empty_without_figures():
    m = SharedMemory()                  # no figures
    assert ebitda_bridge_block(m) == ""
    assert dscr_block(m) == ""
    assert procurement_wc_block(m) == ""
    # pis needs only revenue+headcount; with none -> empty
    assert pis_block(m) == ""


def test_blocks_robust_to_bad_figures():
    m = SharedMemory()
    m.financial_figures = {"revenue": "lots", "operating_profit": None, "total_debt": float("nan")}
    m.annual_revenue = 0
    # must not raise
    assert isinstance(ebitda_bridge_block(m), str)
    assert isinstance(dscr_block(m), str)
    assert isinstance(procurement_wc_block(m), str)
    assert isinstance(pis_block(m), str)


def test_high_pis_requires_audit():
    m = SharedMemory()
    m.annual_revenue = 400_000_000; m.headcount = 60   # 60 + 400 + 1 = 461 -> audited
    b = pis_block(m)
    assert "AUDITED" in b
