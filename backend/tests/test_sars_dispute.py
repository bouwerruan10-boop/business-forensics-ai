"""SARS dispute-deadline tests (TAA business days incl. holidays + dies-non)."""
from datetime import date
from services import sars_dispute as sd


def test_weekend_skip():
    # Mon 2 Feb + 5 business days -> next Mon
    assert sd.add_business_days(date(2026, 2, 2), 5).isoformat() == "2026-02-09"
    assert sd.add_business_days(date(2026, 2, 2), 10).isoformat() == "2026-02-16"


def test_public_holiday_skip():
    # 1 May 2026 is Workers' Day (Fri) -> Thu 30 Apr + 1 bd lands on Mon 4 May
    assert sd.add_business_days(date(2026, 4, 30), 1).isoformat() == "2026-05-04"


def test_dies_non_recess_excluded():
    # 16 Dec - 15 Jan are not business days; Mon 14 Dec + 2 bd jumps to 18 Jan
    assert sd.add_business_days(date(2026, 12, 14), 2).isoformat() == "2027-01-18"


def test_is_business_day():
    assert sd.is_business_day(date(2026, 2, 2)) is True       # Monday
    assert sd.is_business_day(date(2026, 2, 7)) is False      # Saturday
    assert sd.is_business_day(date(2026, 4, 27)) is False     # Freedom Day
    assert sd.is_business_day(date(2026, 12, 20)) is False    # dies non


def test_dispute_timeline_structure():
    r = sd.dispute_timeline("2026-02-02")
    assert r["available"] is True
    keys = [s["key"] for s in r["steps"]]
    assert keys == ["request_reasons", "objection", "sars_decision", "appeal"]
    objection = next(s for s in r["steps"] if s["key"] == "objection")
    assert objection["business_days"] == 80
    assert objection["deadline"] == "2026-05-29"


def test_robust_to_bad_input():
    assert sd.dispute_timeline("not-a-date")["available"] is False
    assert sd.dispute_timeline(None)["available"] is False
