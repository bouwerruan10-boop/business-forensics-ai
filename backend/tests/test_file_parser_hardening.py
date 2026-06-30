"""Hardening: file_parser must be TOTAL (never raise) and FAST on malformed/hostile uploads.
Pressure-test (2026-06-21) found a hang on a giant cell + 3 crashes; these lock the fixes.
The 2026-06-30 sweep added the Excel/PDF paths (previously untested) + an xlsx zip-bomb guard."""
import io
import time
import zipfile

import services.file_parser as fp
from services.file_parser import parse_file, merge_parsed_data


def test_giant_numeric_cell_does_not_hang():
    # A long value used to fall through to dateutil's parser and hang; must be instant + graceful.
    r = parse_file("x.csv", b"Item,Amount\nX," + b"9" * 60_000 + b"\n")
    assert isinstance(r, dict)


def test_giant_text_cell_graceful():
    assert isinstance(parse_file("x.csv", b"Item,Amount\n" + b"Z" * 60_000 + b",100\n"), dict)


def test_cell_value_is_truncated():
    r = parse_file("x.csv", b"Item,Amount\nX," + b"9" * 60_000 + b"\n")
    assert "9" * 3000 not in str(r)   # capped at _MAX_CELL_CHARS, not the full 60k blob


def test_none_filename_does_not_raise():
    assert isinstance(parse_file(None, b"Rev,100\n"), dict)


def test_none_content_graceful():
    r = parse_file("x.csv", None)
    assert isinstance(r, dict) and "error" in r.get("general", {})


def test_oversize_file_rejected_gracefully(monkeypatch):
    monkeypatch.setattr(fp, "MAX_CONTENT_BYTES", 100)
    r = fp.parse_file("x.csv", b"x" * 500)
    assert isinstance(r, dict) and "too large" in r["general"].get("error", "")


def test_merge_skips_none_and_nondict_entries():
    m = merge_parsed_data([None, {"financial": {"x": 1}}, "junk", 42, {"hr": {"y": 2}}])
    assert m == {"financial": {"x": 1}, "hr": {"y": 2}}


def test_normal_csv_still_extracts():
    r = parse_file("fin.csv", b"Item,Amount\nRevenue,5000000\nCosts,3000000\n")
    assert isinstance(r, dict) and "5000000" in (r.get("text", "") or "")


# ── Excel / PDF paths (zero coverage before the 2026-06-30 sweep) ────────────

def test_garbage_bytes_every_binary_extension_total():
    """Garbage/empty bytes routed through the Excel + PDF parsers must return a dict, not raise."""
    import os
    for ext in (".xlsx", ".xls", ".xlsm", ".xlsb", ".pdf"):
        assert isinstance(parse_file("f" + ext, os.urandom(4000)), dict)
        assert isinstance(parse_file("f" + ext, b""), dict)
    # extension lies about content (pdf magic in an .xlsx, html in an .xls)
    assert isinstance(parse_file("f.xlsx", b"%PDF-1.4\n" + os.urandom(2000)), dict)
    assert isinstance(parse_file("f.xls", b"<html><body><script>x</script></body></html>"), dict)


def test_hostile_xlsx_many_sheets_total():
    """A real workbook with >MAX_SHEETS sheets carrying formulas / inf / 400-digit / injection /
    unicode must parse to a dict quickly (the Excel path exercised end-to-end)."""
    import pandas as pd
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        for s in range(fp.MAX_SHEETS + 10):
            pd.DataFrame({
                "Item": ["Revenue", "=1/0", "=cmd|'/c calc'!A1", "<script>x</script>", "中文", "z" * 5000],
                "Amount": ["9" * 400, 1e308, float("inf"), -1e308, "NaN", 0],
            }).to_excel(w, sheet_name="S%d" % s, index=False)
    t = time.time()
    r = parse_file("hostile.xlsx", bio.getvalue())
    assert isinstance(r, dict) and (time.time() - t) < 8


def test_malformed_pdf_total():
    for body in (b"%PDF-1.4\n%%EOF\n", b"%PDF-1.7\n" + b"\x00" * 1000, b"not a pdf at all"):
        assert isinstance(parse_file("f.pdf", body), dict)


# ── xlsx decompression-bomb guard ───────────────────────────────────────────

def test_xlsx_decompression_bomb_rejected_instantly():
    """An xlsx is a zip; deflate hits ~1000x so a tiny upload can declare GBs uncompressed and
    OOM the worker when openpyxl loads the sheet. The guard reads only the central directory
    (no decompression) and rejects it instantly."""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/worksheets/sheet1.xml", b"0" * (fp._MAX_XLSX_UNCOMPRESSED_BYTES + 50 * 1024 * 1024))
    t = time.time()
    r = parse_file("bomb.xlsx", bio.getvalue())
    assert isinstance(r, dict)
    assert "bomb" in (r.get("error", "") or "").lower()
    assert (time.time() - t) < 2, "guard must not decompress"


def test_normal_xlsx_not_falsely_rejected():
    import pandas as pd
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        pd.DataFrame({"Item": ["Revenue", "Costs"], "Amount": [5000000, 3000000]}).to_excel(
            w, index=False, sheet_name="P&L")
    r = parse_file("real.xlsx", bio.getvalue())
    assert isinstance(r, dict) and not r.get("error")
    assert "5000000" in (r.get("text", "") or "")
