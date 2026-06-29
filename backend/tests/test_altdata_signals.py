"""Alternative-data overlay (M2): thin-file cash-flow signals for informal SMEs."""
from services.altdata_signals import analyze_altdata_statement

_MOMO = "\n".join([
    "2026-01-05 MoMo settlement received R 1,200.00",
    "2026-01-12 Mobile money payout R 980.00",
    "2026-01-20 Wallet settlement received R 1,500.00",
    "2026-02-03 MoMo settlement received R 1,100.00",
    "2026-02-15 Mobile money payout R 1,050.00",
    "2026-02-26 Wallet settlement received R 1,300.00",
    "2026-03-04 MoMo settlement received R 1,250.00",
    "2026-03-18 Mobile money payout R 990.00",
    "2026-03-29 Wallet settlement received R 1,400.00",
    "2026-03-30 MoMo settlement received R 1,150.00",
    "2026-03-31 Mobile money payout R 1,020.00",
])

_BANK = "\n".join([
    "2026-01-05 EFT credit salary R 25,000.00 35,000.00",
    "2026-01-06 Debit order insurance R 1,200.00 33,800.00",
    "2026-01-10 POS purchase Woolworths R 800.00 33,000.00",
    "2026-01-12 ATM withdrawal R 2,000.00 31,000.00",
])


def test_momo_statement_scores():
    a = analyze_altdata_statement(_MOMO)
    assert a["available"] is True
    assert a["channel"] == "mobile_money"
    assert a["period_months"] == 3 and a["settlement_inflow_rows"] >= 8
    assert 0 <= a["altdata_health_score"] <= 100 and a["altdata_health_tier"] in ("strong", "adequate", "weak")
    assert a["thin_file_rescue"] is True
    assert "not a component of the imara score" in a["note"].lower()   # overlay discipline


def test_normal_bank_statement_does_not_trigger():
    # POS/ATM keywords appear, but no settlement/momo/wallet markers -> not alt-data
    assert analyze_altdata_statement(_BANK)["available"] is False


def test_reversals_penalise_score():
    clean = analyze_altdata_statement(_MOMO)["altdata_health_score"]
    withrev = analyze_altdata_statement(
        _MOMO + "\n2026-03-31 MoMo settlement reversal R 1,150.00\n"
        "2026-03-31 Wallet chargeback R 1,300.00")["altdata_health_score"]
    assert withrev < clean


def test_short_and_hostile_text_safe():
    for bad in (None, "", "x", "no markers here just text " * 5):
        r = analyze_altdata_statement(bad)
        assert r["available"] is False
