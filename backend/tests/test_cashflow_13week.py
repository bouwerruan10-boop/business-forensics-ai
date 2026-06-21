"""Tests for the deterministic 13-week direct-method cash-flow projection."""
from services.cashflow_13week import project_13week, from_report, cashflow_summary_block, WEEKS
from memory.shared_memory import SharedMemory

_PROFITABLE = {
    "revenue": 12_000_000, "cogs": 8_700_000, "gross_profit": 3_300_000, "operating_profit": 300_000,
    "current_assets": 4_600_000, "receivables": 2_300_000, "inventory": 1_900_000, "total_debt": 2_200_000,
}


def test_profitable_projection_numbers():
    r = project_13week(_PROFITABLE, vat_registered=True)
    assert r["available"] is True
    assert len(r["weeks"]) == WEEKS == 13
    assert r["opening_cash"] == 400_000              # 4.6M - 2.3M - 1.9M
    assert r["weekly_inflow"] == round(12_000_000 / 52)   # 230,769
    assert r["weekly_operating_net"] == round(300_000 / 52)  # 5,769
    assert r["debt_service_monthly"] == 54_045       # 648,542 / 12
    assert r["vat_remittance"] == 82_500             # 0.15 * 3.3M / 6
    assert r["goes_negative"] is False               # healthy buffer + positive run-rate


def test_lumps_land_on_the_right_weeks():
    r = project_13week(_PROFITABLE, vat_registered=True)
    wk = {w["week"]: w for w in r["weeks"]}
    assert any(l["label"] == "Loan instalment" for l in wk[4]["lumps"])
    assert any(l["label"] == "Loan instalment" for l in wk[9]["lumps"])
    assert any(l["label"] == "VAT remittance" for l in wk[8]["lumps"])
    assert wk[1]["lumps"] == []                      # no lump in an ordinary week


def test_loss_maker_runs_out_of_cash():
    loss = {"revenue": 6_000_000, "cogs": 5_200_000, "gross_profit": 800_000, "operating_profit": -600_000,
            "current_assets": 500_000, "receivables": 300_000, "inventory": 150_000, "total_debt": 1_000_000}
    r = project_13week(loss)
    assert r["goes_negative"] is True
    assert 1 <= r["negative_week"] <= 13
    assert r["min_balance"] < 0


def test_unavailable_without_core_figures():
    assert project_13week({}).get("available") is False
    assert project_13week({"revenue": 1_000_000}).get("available") is False   # no operating_profit


def test_opening_cash_unknown_without_balance_sheet():
    r = project_13week({"revenue": 12_000_000, "operating_profit": 300_000})
    assert r["available"] is True
    assert r["opening_known"] is False
    assert r["opening_cash"] == 0


def test_robust_to_bad_figures():
    bad = {"revenue": "lots", "operating_profit": None, "total_debt": float("nan"),
           "current_assets": "x", "receivables": None}
    r = project_13week(bad)               # revenue uncoerceable -> not available, no crash
    assert r.get("available") is False


def test_from_report_and_summary_block():
    rep = {"financial_figures": _PROFITABLE}
    r = from_report(rep, None)
    assert r["available"] is True
    m = SharedMemory(); m.financial_figures = _PROFITABLE; m.vat_registered = True
    block = cashflow_summary_block(m)
    assert "13-WEEK LIQUIDITY HORIZON" in block
    assert "Cash low point" in block
