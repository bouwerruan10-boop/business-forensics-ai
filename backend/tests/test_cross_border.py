"""Cross-border tax tests: s9H exit tax + s10(1)(o)(ii) foreign-income exemption."""
import pytest
from services.exit_tax import assess_exit_tax
from services.foreign_income import assess_foreign_employment


def test_exit_tax_individual_reuses_cgt():
    # R2m deemed gain, individual: net 1,950,000 -> TCG 40% = 780,000
    r = assess_exit_tax(2_000_000, "individual", other_taxable_income=0, age=40)
    assert r["taxable_capital_gain"] == pytest.approx(780_000.0)
    assert r["exit_tax_payable"] > 0


def test_exit_tax_company_80pct_inclusion():
    # company: no annual exclusion, 80% inclusion, 27% -> 2m*0.8*0.27 = 432,000
    r = assess_exit_tax(2_000_000, "company")
    assert r["taxable_capital_gain"] == pytest.approx(1_600_000.0)
    assert r["exit_tax_payable"] == pytest.approx(432_000.0)


def test_exit_tax_robust():
    assert assess_exit_tax("x")["exit_tax_payable"] == 0.0
    assert assess_exit_tax(None)["exit_tax_payable"] == 0.0


def test_foreign_income_qualifies_caps_at_1_25m():
    r = assess_foreign_employment(1_500_000, 200, 70)
    assert r["qualifies"] is True
    assert r["exempt_amount"] == pytest.approx(1_250_000.0)
    assert r["taxable_amount"] == pytest.approx(250_000.0)


def test_foreign_income_below_cap_fully_exempt():
    r = assess_foreign_employment(800_000, 200, 70)
    assert r["exempt_amount"] == pytest.approx(800_000.0)
    assert r["taxable_amount"] == pytest.approx(0.0)


def test_foreign_income_fails_continuous_60():
    r = assess_foreign_employment(1_500_000, 200, 40)
    assert r["qualifies"] is False
    assert r["exempt_amount"] == 0.0
    assert r["taxable_amount"] == pytest.approx(1_500_000.0)


def test_foreign_income_fails_total_183():
    r = assess_foreign_employment(1_500_000, 150, 70)
    assert r["qualifies"] is False


def test_foreign_income_robust():
    assert assess_foreign_employment(None, None, None)["qualifies"] is False
