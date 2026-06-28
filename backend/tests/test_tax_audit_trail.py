"""SARS-cited tax audit-trail tests (provenance per figure + immutable record)."""
from services.tax_assessment import assess_all
from services.tax_audit_trail import build_tax_audit_trail, record_tax_audit


def _assessment():
    return assess_all({
        "income": {"salary": 600000, "age": 40, "paye_paid": 120000},
        "cgt": {"total_gains": 200000, "taxpayer": "individual", "other_taxable_income": 600000, "age": 40},
        "foreign_income": {"foreign_employment_income": 1_500_000, "days_outside_total": 200, "longest_continuous_days": 70},
    })


def test_trail_cites_each_section_with_figures():
    t = build_tax_audit_trail(_assessment())
    assert t["available"] is True and t["count"] == 3
    by = {e["section"]: e for e in t["entries"]}
    assert "income_tax" in by and "cgt" in by and "foreign_income" in by
    assert "8th Schedule" in by["cgt"]["provision"]
    assert "s10(1)(o)(ii)" in by["foreign_income"]["provision"]
    # headline figures are surfaced for tracing
    assert "cgt_payable" in by["cgt"]["figures"]
    assert by["income_tax"]["figures"]["tax_payable"] > 0


def test_trail_includes_dated_rate_source():
    t = build_tax_audit_trail(_assessment())
    assert t["rates_dated"]            # sa_rates.AS_OF surfaced
    assert "superseded" in t["note"].lower()    # the re-verify / supersession check


def test_trail_robust():
    assert build_tax_audit_trail({})["available"] is False
    assert build_tax_audit_trail("x")["available"] is False
    assert build_tax_audit_trail(None)["available"] is False


def test_record_is_immutable_and_chain_verifies(tmp_path, monkeypatch):
    import services.database as db
    monkeypatch.setattr(db, "_DB_PATH", tmp_path / "audit.db")
    db.init_db()
    res = record_tax_audit("a-9", _assessment())
    assert res["recorded"] is True and res["record_hash"]
    assert set(res["sections"]) == {"income_tax", "cgt", "foreign_income"}
    rows = [r for r in db.get_audit("a-9") if r.get("type") == "tax_audit_trail"]
    assert len(rows) == 1
    assert db.verify_audit_chain()["intact"] is True
