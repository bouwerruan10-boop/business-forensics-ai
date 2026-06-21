"""Tests for the deterministic forensic scanner + its injection into the 3 agents."""
from services.forensic_scan import (
    find_duplicate_amounts, round_number_ratio, forensic_scan, forensic_scan_block,
)
from memory.shared_memory import SharedMemory
from agents import specialist_agents as SA


def test_duplicate_amounts_counts_exactly():
    t = "Salary 45,000 Salary 45,000 Salary 45,000 Big 200,000 Big 200,000 EFT 45,000 Misc 7,777"
    dups = dict(find_duplicate_amounts(t))
    assert dups.get(45000.0) == 4            # 3 salary + 1 EFT
    assert 200000.0 not in dups              # only 2 -> below min_repeats=3
    t2 = t + " Big 200,000"
    assert dict(find_duplicate_amounts(t2)).get(200000.0) == 3


def test_duplicate_amounts_respects_floor():
    # small amounts below the 1000 floor are ignored
    t = "fee 35 fee 35 fee 35 fee 35"
    assert find_duplicate_amounts(t) == []


def test_round_number_ratio_needs_enough_data():
    assert round_number_ratio("100,000 200,000") is None       # <10 large figures
    big = " ".join(["50,000"] * 8 + ["13,482", "26,913"])      # 10 figures, 8 round
    r = round_number_ratio(big)
    assert r is not None and 0.7 <= r <= 0.85


def test_scan_robust_to_bad_input():
    class Bag: pass
    for bad in [Bag(),
                type("X", (), {"uploaded_financial_text": None, "uploaded_bank_text": None})(),
                type("Y", (), {"uploaded_financial_text": 123, "uploaded_bank_text": ["a"]})()]:
        b = forensic_scan_block(bad)
        assert "DETERMINISTIC ANOMALY CANDIDATES" in b            # no crash, always renders


def _capture_prompt(cls, memory):
    cap = []
    cls._call_claude = lambda self, p, *a, **k: (cap.append(p) or "No findings.")
    cls().analyze({"financial": {}, "accounting": {}}, memory)
    return "\n".join(cap)


def test_scanner_injected_into_all_three_forensic_agents():
    m = SharedMemory()
    m.business_name = "T"; m.industry = "retail"; m.annual_revenue = 8_000_000; m.headcount = 15
    m.currency = "ZAR"; m.country = "South Africa"
    m.uploaded_financial_text = "Salary 45,000 Salary 45,000 Salary 45,000 Big 200,000 Big 200,000 Big 200,000"
    m.uploaded_bank_text = "EFT 45,000 EFT 45,000"
    for cls in (SA.AccountingAgent, SA.AuditorAgent, SA.FraudDetectionAgent):
        blob = _capture_prompt(cls, m)
        assert "DETERMINISTIC ANOMALY CANDIDATES" in blob
        assert "R45,000" in blob              # the detected duplicate surfaces to the agent
