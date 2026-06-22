"""Hardening: file_parser must be TOTAL (never raise) and FAST on malformed/hostile uploads.
Pressure-test (2026-06-21) found a hang on a giant cell + 3 crashes; these lock the fixes."""
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
