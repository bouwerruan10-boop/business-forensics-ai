"""Hardening: the untrusted-text -> number extractors must never emit inf/nan into the
figures that feed the Imara Score (pressure-test 2026-06-21 found parse_amount -> inf)."""
import math
from services.financial_ratios import parse_amount, extract_financials, compute_ratios
from services.bank_signals import _to_float
from services.expense_lines import _amount


def test_parse_amount_rejects_overflow_inf():
    assert parse_amount("9" * 2_000_000) is None          # would have been float('inf')
    assert parse_amount("9" * 400) is None                # ~1e400 overflows to inf -> rejected


def test_to_float_rejects_overflow_inf():
    assert _to_float("9" * 2_000_000) is None


def test_extract_financials_never_returns_nonfinite():
    figs = extract_financials("revenue " + "9" * 2_000_000)
    rev = figs.get("revenue")
    assert rev is None or math.isfinite(rev)


def test_amount_is_always_finite():
    v = _amount("X " + "9" * 2_000_000)
    assert v is None or math.isfinite(v)


def test_compute_ratios_emits_no_nonfinite():
    r = compute_ratios({"revenue": 5_000_000, "cogs": 3_000_000, "net_profit": 400_000,
                        "current_assets": 1_500_000, "current_liabilities": 900_000})
    for k, v in r.items():
        if isinstance(v, float):
            assert math.isfinite(v), f"{k} is non-finite: {v}"


def test_normal_parsing_unchanged():
    assert parse_amount("R 1,200,000") == 1_200_000.0
    assert parse_amount("(500)") == -500.0
    assert parse_amount("1.2m") == 1_200_000.0
    assert _amount("Rent 120,000") == 120_000.0
    assert extract_financials("Revenue 5,000,000\nNet profit 400,000") == {"revenue": 5_000_000.0, "net_profit": 400_000.0}


# ── /api/analyze ingestion: file_categories must never crash the endpoint (pressure-test) ──
from main import _coerce_categories


def test_coerce_categories_total_on_hostile_input():
    # number / null / bool used to crash the handler with len() TypeError -> 500
    for raw in ("123", "null", "true", '"financial"', '[{"a":1}]', "{}", "[1,null]", "not json", ""):
        out = _coerce_categories(raw, 2)
        assert isinstance(out, list) and len(out) == 2 and all(isinstance(x, str) for x in out)


def test_coerce_categories_preserves_valid_and_pads():
    assert _coerce_categories('["financial","bank"]', 2) == ["financial", "bank"]
    assert _coerce_categories('["tax"]', 3) == ["tax", "general", "general"]   # short list padded
    assert _coerce_categories('["a","b","c"]', 1) == ["a"]                      # long list truncated to n
    assert _coerce_categories("[]", 0) == []
