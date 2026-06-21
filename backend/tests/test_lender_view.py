"""
Unit tests for the research-driven "Lender's-Eye View" builds:
  - services/normalization.py  (Adjusted EBITDA / owner add-backs + SA loan-account flag)
  - services/lender_view.py    (reconciliation, cash-flow conduct, borrowing capacity, decline-risk)
All deterministic, no API.
"""
from services.normalization import normalize_earnings, detect_loan_account
from services.lender_view import run_lender_view
from services.bank_signals import analyze_bank_statement

_FIN = ("Revenue 12 000 000\nOperating profit 900 000\nDepreciation 300 000\n"
        "Directors remuneration 1 200 000\nMotor vehicle expenses 180 000\n"
        "Entertainment 90 000\nDonations 40 000\nRestructuring costs 250 000\nDrawings 500 000\n")

_HEALTHY_BANK = ("Date Description Amount Balance\n"
                 "01/03/2026 Deposit client payment received 300,000.00 420,000.00\n"
                 "05/03/2026 Salaries debit order payment 90,000.00 330,000.00\n"
                 "12/03/2026 Deposit eft in received 280,000.00 610,000.00\n"
                 "02/04/2026 Deposit received 310,000.00 860,000.00\n"
                 "20/04/2026 Deposit incoming received 295,000.00 955,000.00\n"
                 "03/05/2026 Deposit client received 305,000.00 1,200,000.00\n")

_DISTRESSED_BANK = ("Date Description Amount Balance\n"
                    "01/03/2026 Deposit received 120,000.00 35,000.00\n"
                    "05/03/2026 Debit order RETURNED unpaid R/D 60,000.00 -25,000.00\n"
                    "12/03/2026 Overdraft fees charge 1,200.00 -26,200.00\n"
                    "02/04/2026 Deposit received 90,000.00 -5,000.00\n")


# ── normalization ──────────────────────────────────────────────────────────
def test_normalization_derives_ebitda_and_addbacks():
    r = normalize_earnings({"revenue": 12_000_000, "operating_profit": 900_000}, _FIN)
    assert r["available"]
    assert r["ebitda_basis"] == "estimated_from_operating_profit"
    assert r["reported_ebitda"] == 1_200_000  # 900k operating + 300k D&A
    labels = " ".join(a["label"] for a in r["add_backs"])
    assert "Donations" in labels and "Restructuring" in labels
    # conservative (one-offs only) strictly below optimistic (incl. owner-personal)
    assert r["adjusted_ebitda_low"] < r["adjusted_ebitda_high"]
    assert r["adjusted_ebitda_low"] == 1_200_000 + 40_000 + 250_000


def test_normalization_uses_reported_ebitda_when_present():
    r = normalize_earnings({"ebitda": 2_000_000}, "Donations 50 000\n")
    assert r["ebitda_basis"] == "reported"
    assert r["reported_ebitda"] == 2_000_000
    assert r["adjusted_ebitda_low"] == 2_050_000


def test_normalization_graceful_without_figures():
    r = normalize_earnings({}, _FIN)
    assert r["available"] is False and "reason" in r


def test_normalization_coerces_string_figures():
    r = normalize_earnings({"ebitda": "1 000 000"}, "")
    assert r["available"] and r["reported_ebitda"] == 1_000_000.0


def test_loan_account_flag():
    f = detect_loan_account("Owner funds living costs via the director's loan account and drawings each month.", "")
    assert f["flagged"] and f["level"] == "high"
    assert "SARS" in f["detail"] or "deemed dividend" in f["detail"]
    assert detect_loan_account("Salaries 800 000 PAYE remitted", "")["flagged"] is False


# ── lender_view ────────────────────────────────────────────────────────────
def _lv(figs, bank_text, annual_revenue=12_000_000):
    bank = analyze_bank_statement(bank_text)
    norm = normalize_earnings(figs, _FIN)
    return run_lender_view(figs, bank, norm, annual_revenue), bank


def test_lender_view_distressed_is_high_risk():
    figs = {"revenue": 600_000, "operating_profit": 50_000}
    lv, bank = _lv(figs, _DISTRESSED_BANK, 600_000)
    assert bank["returned_debit_orders"] >= 1
    assert lv["decline_risk"] == "high"
    issues = " ".join(r["issue"] for r in lv["reasons"])
    assert "bounced" in issues.lower() or "returned" in issues.lower()
    # every reason carries a concrete fix
    assert all(r["fix"] for r in lv["reasons"])


def test_lender_view_healthy_reconciles_and_lower_risk():
    figs = {"revenue": 3_600_000, "operating_profit": 700_000}
    lv, bank = _lv(figs, _HEALTHY_BANK, 3_600_000)
    assert bank["returned_debit_orders"] == 0
    assert lv["decline_risk"] in ("low", "medium")
    assert lv["cash_flow_metrics"]["average_daily_balance"] is not None
    assert lv["borrowing_capacity"]["working_capital_facility"] is not None


def test_lender_view_reconciliation_guards_implausible_parse():
    # tiny deposits vs huge declared revenue -> inconclusive, NOT a false "revenue overstated" red flag
    figs = {"revenue": 120_000_000, "operating_profit": 5_000_000}
    lv, _ = _lv(figs, _HEALTHY_BANK, 120_000_000)
    assert lv["reconciliation"]["direction"] == "inconclusive"
    assert lv["reconciliation"]["material"] is False


def test_lender_view_no_bank_is_graceful():
    figs = {"revenue": 3_600_000, "operating_profit": 700_000}
    lv = run_lender_view(figs, {"available": False}, normalize_earnings(figs, _FIN), 3_600_000)
    assert lv["available"] and lv["decline_risk"] in ("low", "medium", "high")
    assert lv["cash_flow_metrics"]["available"] is False


def test_lender_view_handles_empty_inputs():
    lv = run_lender_view({}, {}, {})
    assert lv["available"] and "decline_risk" in lv


def test_nonfinite_figures_stay_json_safe():
    """NaN/inf figures must not leak into outputs (would break JSON / the frontend)."""
    import json
    for figs in ({"ebitda": float("nan")}, {"ebitda": float("inf")}, {"operating_profit": "inf"}):
        nm = normalize_earnings(figs, "Donations 50 000\n")
        lv = run_lender_view(figs, {"available": False}, nm, 1_000_000)
        json.dumps(nm, allow_nan=False)   # raises if NaN/inf present
        json.dumps(lv, allow_nan=False)
        assert nm["available"] is False
