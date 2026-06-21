"""Unit tests for the Bank-Ready Pack PDF generator (deterministic, no API)."""
from services.bank_ready_pack import generate_bank_ready_pack


def _rich():
    return {
        "business_name": "Test (Pty) Ltd", "currency": "ZAR", "industry": "Retail",
        "entity_type": "Private company", "banking_partner": "Standard Bank",
        "financial_figures": {"revenue": 12_000_000, "operating_profit": 900_000, "net_profit": 300_000},
        "normalization": {"available": True, "reported_ebitda": 1_200_000, "ebitda_basis": "reported",
                          "add_backs": [{"label": "Donations", "amount": 40_000, "confidence": "high", "note": "Non-recurring"},
                                        {"label": "Owner vehicle", "amount": 120_000, "confidence": "owner-confirm", "note": "confirm portion"}],
                          "add_backs_total_conservative": 40_000, "add_backs_total_optimistic": 160_000,
                          "adjusted_ebitda_low": 1_240_000, "adjusted_ebitda_high": 1_360_000,
                          "loan_account_flag": {"flagged": True, "level": "medium", "detail": "d", "fix": "f"}},
        "lender_view": {"available": True, "decline_risk": "high", "verdict": "Would likely decline.",
                        "reasons": [{"severity": "high", "issue": "bounced debit orders here", "fix": "fund the account"}],
                        "reconciliation": {"available": True, "declared_revenue": 12_000_000, "annualized_deposits": 11_800_000,
                                           "gap_pct": -1.7, "interpretation": "reconciles"},
                        "cash_flow_metrics": {"available": True, "period_months": 3, "average_daily_balance": 500_000,
                                              "average_monthly_deposits": 980_000, "deposit_consistency": "consistent",
                                              "returned_debit_orders": 1, "min_balance": -1000},
                        "borrowing_capacity": {"working_capital_facility": {"low": 784_000, "high": 1_470_000, "basis": "b"},
                                               "term_loan": {"implied_principal_low": 2_000_000, "implied_principal_high": 2_500_000,
                                                             "supportable_annual_debt_service_low": 800_000, "supportable_annual_debt_service_high": 960_000, "basis": "b"},
                                               "assumptions": "indicative"}},
        "financial_ratios": {"gross_margin": {"label": "Gross Margin", "value": 18.0, "unit": "%", "benchmark": 30.0, "status": "critical"},
                             "debtor_days": {"label": "Debtor Days", "value": 53.6, "unit": "days", "benchmark": 35, "status": "critical"}},
    }


def test_pack_generates_valid_pdf():
    b = generate_bank_ready_pack(_rich())
    assert b[:4] == b"%PDF" and len(b) > 1500


def test_pack_graceful_on_sparse_inputs():
    for rep in (None, {}, {"financial_figures": None, "lender_view": None, "bank_signals": None},
                {"business_name": "X", "currency": "ZAR", "financial_figures": {"revenue": 1_000_000}}):
        b = generate_bank_ready_pack(rep)
        assert b[:4] == b"%PDF"


def test_pack_handles_nonfinite_and_string_figures():
    rep = _rich()
    rep["financial_figures"] = {"revenue": "12 000 000", "operating_profit": float("inf")}
    rep["normalization"]["reported_ebitda"] = float("nan")
    b = generate_bank_ready_pack(rep)   # must not crash
    assert b[:4] == b"%PDF"


def test_pack_survives_wrong_typed_sections():
    """Report subsections may be the wrong type (string/list/int) — must still yield a valid PDF."""
    for sub in ("financial_figures", "normalization", "lender_view", "bank_signals", "financial_ratios"):
        for val in ("garbage", ["a", "b"], 123, True):
            b = generate_bank_ready_pack({sub: val, "business_name": "X"})
            assert b[:4] == b"%PDF"
    # non-string business_name and nested wrong types
    assert generate_bank_ready_pack({"business_name": 12345, "annual_revenue": float("inf")})[:4] == b"%PDF"
    assert generate_bank_ready_pack({"normalization": {"available": True, "reported_ebitda": 1e6,
        "adjusted_ebitda_low": 1e6, "adjusted_ebitda_high": 2e6, "add_backs": "nope",
        "loan_account_flag": "nope"}})[:4] == b"%PDF"
    assert generate_bank_ready_pack({"lender_view": {"available": True, "decline_risk": "high",
        "verdict": "v", "reasons": "nope", "reconciliation": "nope",
        "cash_flow_metrics": "nope", "borrowing_capacity": "nope"}})[:4] == b"%PDF"
