"""Deterministic VAT computation tests (15/115 fraction + VAT201 net position)."""
import pytest
from services import vat_calc
from services.sa_rates import VAT_RATE


def test_tax_fraction_is_15_over_115():
    assert VAT_RATE == 15.0
    assert vat_calc.tax_fraction() == pytest.approx(15.0 / 115.0)


def test_split_inclusive():
    s = vat_calc.split_inclusive(1150)
    assert s["vat"] == pytest.approx(150.0)
    assert s["excl"] == pytest.approx(1000.0)
    assert s["incl"] == pytest.approx(1150.0)


def test_add_vat():
    a = vat_calc.add_vat(1000)
    assert a["vat"] == pytest.approx(150.0)
    assert a["incl"] == pytest.approx(1150.0)


def test_vat201_payable():
    # R115,000 incl standard-rated sales -> R15,000 output; R23,000 incl inputs -> R3,000 input
    r = vat_calc.compute_vat201(standard_rated_incl=115_000, input_other_incl=23_000)
    assert r["output"]["output_vat"] == pytest.approx(15_000.0)
    assert r["input"]["total_input_vat"] == pytest.approx(3_000.0)
    assert r["net_vat_payable"] == pytest.approx(12_000.0)
    assert r["net_position"] == "payable"
    assert r["tax_fraction_label"] == "15/115"
    assert r["output"]["standard_rated_supplies_excl"] == pytest.approx(100_000.0)


def test_vat201_refund_when_inputs_exceed_outputs():
    r = vat_calc.compute_vat201(standard_rated_incl=11_500, input_capital_incl=115_000)
    assert r["net_vat_payable"] < 0
    assert r["net_position"] == "refund"
    assert r["input"]["capital_goods_vat"] == pytest.approx(15_000.0)


def test_vat201_excl_supplies_and_zero_exempt():
    r = vat_calc.compute_vat201(standard_rated_excl=100_000, zero_rated=50_000, exempt=20_000)
    assert r["output"]["output_vat"] == pytest.approx(15_000.0)   # 15% of excl
    assert r["output"]["zero_rated_supplies"] == pytest.approx(50_000.0)
    assert r["output"]["exempt_supplies"] == pytest.approx(20_000.0)


def test_vat201_nil_position():
    r = vat_calc.compute_vat201(standard_rated_incl=115_000, input_other_incl=115_000)
    assert r["net_position"] == "nil"
    assert r["net_vat_payable"] == pytest.approx(0.0)


def test_robust_to_none_and_garbage():
    r = vat_calc.compute_vat201(standard_rated_incl=None, input_other_incl="oops", zero_rated=-5)
    assert r["output"]["output_vat"] == 0.0
    assert r["input"]["total_input_vat"] == 0.0
    assert r["net_position"] == "nil"
    assert r["output"]["zero_rated_supplies"] == 0.0   # negative coerced to 0


def test_rate_override():
    assert vat_calc.tax_fraction(rate=14) == pytest.approx(14.0 / 114.0)
