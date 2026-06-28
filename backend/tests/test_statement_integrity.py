"""Bank-statement integrity tests: forward balance reconciliation + PDF-metadata fraud signals."""
import io
import pytest

from services.statement_integrity import (
    reconcile_balances, check_pdf_metadata, assess_statement_integrity, _to_float,
)


# ---- amount parsing (SA formats) ----

def test_amount_parser_handles_sa_formats():
    assert _to_float("R 1 234 567.89") == pytest.approx(1234567.89)
    assert _to_float("1,234.56") == pytest.approx(1234.56)
    assert _to_float("1 234,56") == pytest.approx(1234.56)        # comma decimal
    assert _to_float("(500.00)") == pytest.approx(-500.0)         # parentheses negative
    assert _to_float("500.00", "Dr") == pytest.approx(-500.0)     # Dr suffix negative
    assert _to_float("rubbish") is None


# ---- forward balance reconciliation ----

def test_reconciliation_ties_out():
    t = ("Opening balance: R1,000.00\nTotal credits: R5,000.00\n"
         "Total debits: R4,000.00\nClosing balance: R2,000.00")
    r = reconcile_balances(t)
    assert r["status"] == "reconciled"
    assert r["expected_closing"] == pytest.approx(2000.0)


def test_reconciliation_detects_discrepancy():
    t = ("Opening balance 1000.00\nTotal credits 5000.00\n"
         "Total debits 4000.00\nClosing balance 2500.00")     # should be 2000
    r = reconcile_balances(t)
    assert r["status"] == "discrepancy"
    assert r["difference"] == pytest.approx(-500.0)


def test_reconciliation_insufficient_is_not_a_pass():
    r = reconcile_balances("A statement with no machine-readable summary totals.")
    assert r["status"] == "insufficient_data"      # honest: never a fabricated pass


def test_reconciliation_robust_to_non_string():
    assert reconcile_balances(None)["status"] == "insufficient_data"
    assert reconcile_balances(12345)["status"] == "insufficient_data"


# ---- PDF metadata fraud signals ----

def _make_pdf(producer, creator="", created=None, modified=None):
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader, PdfWriter
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "Bank Statement")
    c.save()
    buf.seek(0)
    w = PdfWriter()
    w.append_pages_from_reader(PdfReader(buf))
    md = {"/Producer": producer}
    if creator:
        md["/Creator"] = creator
    if created:
        md["/CreationDate"] = created
    if modified:
        md["/ModDate"] = modified
    w.add_metadata(md)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def test_metadata_clean_bank_engine():
    pdf = _make_pdf("Finacle Core Banking", created="D:20240101000000", modified="D:20240101000000")
    r = check_pdf_metadata(pdf)
    assert r["status"] == "clean"
    assert "finacle" in r["bank_engine_detected"]


def test_metadata_editing_tool_is_review():
    r = check_pdf_metadata(_make_pdf("iLovePDF"))
    assert r["status"] == "review"
    assert r["flags"]


def test_metadata_editing_plus_modified_is_likely_tampered():
    pdf = _make_pdf("Adobe Acrobat Pro", created="D:20240101000000", modified="D:20240601120000")
    r = check_pdf_metadata(pdf)
    assert r["status"] == "likely_tampered"
    assert len(r["flags"]) == 2


def test_metadata_robust_to_garbage():
    assert check_pdf_metadata(b"not a pdf")["status"] == "unknown"


# ---- combined assessment ----

def test_assess_overall_elevated_on_discrepancy():
    t = "Opening balance 1000\nTotal credits 5000\nTotal debits 4000\nClosing balance 9999"
    assert assess_statement_integrity(text=t)["overall"] == "elevated"


def test_assess_overall_clean_when_reconciled_and_no_pdf():
    t = "Opening balance 1000\nTotal credits 5000\nTotal debits 4000\nClosing balance 2000"
    assert assess_statement_integrity(text=t)["overall"] == "clean"
