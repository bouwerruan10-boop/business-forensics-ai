"""Orchestrator + /api/tax/income endpoint tests (deterministic, no Claude API)."""
import pytest
from services.tax_assessment import assess_all


def test_income_only():
    r = assess_all({"income": {"salary": 300_000, "paye_paid": 50_000, "age": 30}})
    assert r["income_tax"]["tax_payable"] == pytest.approx(40_572.0)
    assert r["income_tax"]["position"] == "refund"
    assert "vat" not in r and "eti" not in r
    assert "disclaimer" in r


def test_all_sections():
    r = assess_all({
        "income": {"salary": 500_000, "age": 40},
        "vat": {"standard_rated_incl": 115_000, "input_other_incl": 23_000},
        "employees": [{"age": 25, "monthly_remuneration": 3000}],
        "eti_year": 1,
    })
    assert r["income_tax"]["tax_payable"] == pytest.approx(98_417.0)
    assert r["vat"]["net_vat_payable"] == pytest.approx(12_000.0)
    assert r["eti"]["monthly_total"] == pytest.approx(1500.0)


def test_unknown_keys_ignored_no_crash():
    # hostile/extra keys must not raise TypeError into the engines
    r = assess_all({"income": {"salary": 100_000, "evil": "x", "__proto__": 1, "age": 30}})
    assert "income_tax" in r


def test_empty_and_garbage_body():
    assert "income_tax" not in assess_all({})
    assert "income_tax" not in assess_all(None)
    assert assess_all("nope") == {"as_of": "SA 2026/27 tax year",
                                  "disclaimer": assess_all({})["disclaimer"]}


def test_endpoint_smoke():
    from fastapi.testclient import TestClient
    import main
    with TestClient(main.app) as c:
        resp = c.post("/api/tax/income", json={"income": {"salary": 300_000, "age": 30}})
        assert resp.status_code == 200
        assert resp.json()["income_tax"]["taxable_income"] == 300_000.0


def test_provisional_section():
    r = assess_all({"provisional": {"estimate_taxable": 300_000, "age": 30,
                                    "latest_assessed_taxable": 280_000}})
    assert r["provisional"]["tax_on_estimate"] == 300_000.0 * 0 + 40_572.0
    assert r["provisional"]["total_provisional"] == 40_572.0
    assert "income_tax" not in r   # only the provisional section was supplied


def test_cgt_section():
    r = assess_all({"cgt": {"total_gains": 200_000, "taxpayer": "company"}})
    assert r["cgt"]["taxable_capital_gain"] == 160_000.0
    assert r["cgt"]["cgt_payable"] == 43_200.0


def test_fringe_and_lump_sections():
    r = assess_all({
        "fringe_benefits": {"car_determined_value": 400_000, "loan_amount": 500_000},
        "lump_sum": {"amount": 600_000, "kind": "retirement"},
    })
    assert r["fringe_benefits"]["total_taxable_fringe_benefits"] == 206_750.0
    assert r["lump_sum"]["tax"] == 9_000.0
