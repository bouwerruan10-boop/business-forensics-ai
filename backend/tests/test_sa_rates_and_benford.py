"""P0 improvement tests: dated sa_rates config + Benford sample-size gate."""
from services.sa_rates import (
    sa_rates_block, sme_debt_rate_range,
    VAT_COMPULSORY_THRESHOLD, PRIME_RATE, REPO_RATE, SARS_INTEREST_RATE,
)
from memory.shared_memory import SharedMemory
from agents.specialist_agents import _benford_count


def test_current_rates_values():
    assert VAT_COMPULSORY_THRESHOLD == 2_300_000   # Budget 2026
    assert REPO_RATE == 7.00
    assert PRIME_RATE == 10.50                      # repo + 3.5%
    assert SARS_INTEREST_RATE == 10.50


def test_rates_block_contains_current_figures():
    b = sa_rates_block()
    assert "R2,300,000" in b
    assert "10.50%" in b
    assert "R120,000" in b          # voluntary threshold
    assert "+200bps" in b
    # the old stale numbers must not appear
    assert "R1,000,000" not in b
    assert "10.25" not in b


def test_sme_debt_rate_range():
    lo, hi = sme_debt_rate_range()
    assert lo == 13.50 and hi == 15.50


def test_benford_count_gate():
    m = SharedMemory()
    m.uploaded_financial_text = ""
    m.uploaded_bank_text = ""
    assert _benford_count(m) == 0                   # no data -> gate suppresses

    m.uploaded_financial_text = "R12,345 R6,789 100,200 "
    assert _benford_count(m) >= 3                    # counts multi-digit figures

    big = " ".join("%d,%03d" % (i, i % 1000) for i in range(500))
    m.uploaded_financial_text = big
    assert _benford_count(m) >= 300                  # large dataset -> Benford allowed


def test_benford_count_robust_to_nonstring_buckets():
    """Defensive: text buckets are always str in prod, but never crash if not."""
    m = SharedMemory()
    m.uploaded_financial_text = 12345          # wrong type
    m.uploaded_bank_text = ["a", "b"]          # wrong type
    assert _benford_count(m) >= 0              # coerced, no crash
    m.uploaded_financial_text = None
    m.uploaded_bank_text = None
    assert _benford_count(m) == 0
