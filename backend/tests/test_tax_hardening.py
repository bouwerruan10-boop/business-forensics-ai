"""Hardening regression tests for the public /api/tax/income surface.

Locks the adversarial-input fixes: non-finite (inf/nan) never leaks into output
or produces invalid JSON; a hostile roster cannot tie up the worker; huge nested
lists are bounded; type-confused/hostile bodies degrade gracefully.
"""
import json
import pytest
from services.tax_assessment import assess_all, _MAX_LIST
from services import income_tax, tax_residency


def test_non_finite_input_never_leaks_into_output():
    out = assess_all({"income": {"salary": "1e400", "age": 40}})
    assert out["income_tax"]["gross_income"] == 0.0
    # strict JSON: raises if any inf/nan present
    json.dumps(out, allow_nan=False)


def test_multiple_inf_sections_stay_json_safe():
    out = assess_all({
        "income": {"salary": "1e400", "age": 40},
        "vat": {"standard_rated_incl": "1e500"},
        "cgt": {"total_gains": "inf", "taxpayer": "individual"},
    })
    json.dumps(out, allow_nan=False)   # must not raise


def test_nan_coerced_to_zero():
    assert income_tax._num(float("nan")) == 0.0
    assert income_tax._num(float("inf")) == 0.0
    assert income_tax._num("1e400") == 0.0
    assert income_tax._num(50_000) == 50_000.0


def test_roster_is_capped():
    out = assess_all({"employees": [{"age": 25, "monthly_remuneration": 3000}] * 500_000})
    assert len(out["eti"]["employees"]) == _MAX_LIST


def test_residency_prior_years_bounded():
    # a multi-million element list must not be fully iterated; only 5 years count
    r = tax_residency.physical_presence_test(200, [200] * 5_000_000)
    assert r["resident_by_presence"] is True
    assert len(r["prongs"][1]["value"]) == 5


def test_type_confused_body_degrades_gracefully():
    assert assess_all({"income": [1, 2, 3]}).get("income_tax") is None
    assert assess_all({"employees": {"a": 1}}).get("eti") is None
    assert assess_all("not-a-dict")["as_of"]
    assert assess_all(None)["as_of"]


def test_injection_string_does_not_break_or_persist():
    out = assess_all({"cgt": {"total_gains": 100000, "taxpayer": "<script>alert(1)</script>" * 50}})
    # unknown taxpayer normalises to 'individual'; no crash, valid JSON
    assert out["cgt"]["taxpayer"] == "individual"
    json.dumps(out, allow_nan=False)
