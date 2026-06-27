"""SARS TCS 4-pillar readiness tests (registration derived; others verify/honest)."""
from services.tcs_status import build_tcs_status as build


def test_vat_registration_gap_is_action():
    # company over R1m turnover but not VAT-registered -> compulsory-registration gap
    r = build({"entity_type": "Pty Ltd", "annual_revenue": 2_000_000, "vat_registered": "no"})
    assert r["available"] is True
    assert r["pillars"]["registration"]["status"] == "action"
    assert r["overall"] == "action_required"
    assert any(req["tax"] == "VAT" and req["satisfied"] is False
               for req in r["pillars"]["registration"]["required"])


def test_no_gap_defaults_to_verify_not_fabricated_pass():
    # honest by design: with no submission/debt visibility, overall is "verify", never "compliant"
    r = build({"entity_type": "Pty Ltd", "annual_revenue": 800_000, "vat_registered": "yes"})
    assert r["pillars"]["registration"]["status"] == "pass"
    assert r["pillars"]["submission"]["status"] == "verify"
    assert r["pillars"]["debt"]["status"] == "verify"
    assert r["overall"] == "verify_on_efiling"


def test_explicit_signals_drive_pillars():
    r = build({"entity_type": "Pty Ltd", "annual_revenue": 800_000, "vat_registered": "yes",
               "tcs_signals": {"tax_debt": 50_000, "outstanding_returns": True,
                               "outstanding_relevant_material": False}})
    assert r["pillars"]["debt"]["status"] == "action"
    assert r["pillars"]["submission"]["status"] == "action"
    assert r["pillars"]["relevant_material"]["status"] == "pass"
    assert r["overall"] == "action_required"


def test_all_clear_signals_likely_compliant():
    r = build({"entity_type": "Pty Ltd", "annual_revenue": 800_000, "vat_registered": "yes",
               "tcs_signals": {"tax_debt": 0, "outstanding_returns": False,
                               "outstanding_relevant_material": False}})
    assert r["overall"] == "likely_compliant"


def test_employer_requires_paye():
    r = build({"entity_type": "Pty Ltd", "vat_registered": "no", "headcount": 5})
    taxes = [req["tax"] for req in r["pillars"]["registration"]["required"]]
    assert "PAYE / UIF (employer)" in taxes


def test_robust_to_empty_and_hostile():
    assert build({}).get("available") is False
    assert build("nope").get("available") is False
    assert build(None).get("available") is False
