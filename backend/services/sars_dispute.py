"""
sars_dispute.py - deterministic SARS dispute & assessment-deadline calculator.

Pure functions; the LLM only narrates. Given the date of an assessment, returns
each statutory dispute step with its DEADLINE DATE, computed in TAA "business
days". Under s1 of the Tax Administration Act 28/2011 a "business day" EXCLUDES
Saturdays, Sundays, public holidays AND the dies-non period 16 December to 15
January (both inclusive) - so these deadlines are later than a naive weekday count.

Statutory limits (TAA + the Dispute Resolution rules effective 10 March 2023):
- Request for reasons:     30 business days from the assessment (rule 6).
- Objection (NOO/ADR1):    80 business days from the assessment, or from the date
                           reasons were provided/refused (rule 7).
- SARS decides objection:  60 business days after the objection is delivered (rule 9).
- Appeal (NOA/ADR2):       30 business days after the objection is disallowed (rule 10).
Re-verify the day-counts and the public-holiday list against SARS each year.
"""

from datetime import date, timedelta

# SA public holidays 2026 (Sunday holidays observed the following Monday;
# Saturday holidays are NOT moved). Dated - replace yearly. Callers may pass
# their own `holidays` set for other years.
SA_PUBLIC_HOLIDAYS_2026 = frozenset({
    date(2026, 1, 1),    # New Year's Day
    date(2026, 3, 21),   # Human Rights Day (Sat - not moved)
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 6),    # Family Day
    date(2026, 4, 27),   # Freedom Day
    date(2026, 5, 1),    # Workers' Day
    date(2026, 6, 16),   # Youth Day
    date(2026, 8, 9),    # National Women's Day (Sun)
    date(2026, 8, 10),   # observed Women's Day (Mon)
    date(2026, 9, 24),   # Heritage Day
    date(2026, 12, 16),  # Day of Reconciliation
    date(2026, 12, 25),  # Christmas Day
    date(2026, 12, 26),  # Day of Goodwill (Sat - not moved)
})

# (key, label, business-day limit, citation)
DISPUTE_STEPS = (
    ("request_reasons", "Request reasons for the assessment", 30,
     "TAA dispute-resolution rule 6 - within 30 business days of the assessment."),
    ("objection", "Lodge an objection (NOO / online dispute)", 80,
     "TAA s104 + rule 7 - within 80 business days of the assessment (or of reasons)."),
    ("sars_decision", "SARS must decide the objection", 60,
     "TAA rule 9 - SARS notifies its decision within 60 business days of delivery."),
    ("appeal", "Lodge an appeal (NOA) if the objection is disallowed", 30,
     "TAA s107 + rule 10 - within 30 business days of the objection being disallowed."),
)


def _in_dies_non(d):
    """The TAA recess: 16 December to 15 January (both inclusive)."""
    return (d.month == 12 and d.day >= 16) or (d.month == 1 and d.day <= 15)


def is_business_day(d, holidays=SA_PUBLIC_HOLIDAYS_2026):
    """A TAA business day: not a weekend, public holiday, or dies-non day."""
    if d.weekday() >= 5:           # 5 = Sat, 6 = Sun
        return False
    if d in holidays:
        return False
    return not _in_dies_non(d)


def add_business_days(start, n, holidays=SA_PUBLIC_HOLIDAYS_2026):
    """The date that is `n` TAA business days after `start` (start day excluded)."""
    d = start
    remaining = int(n)
    while remaining > 0:
        d = d + timedelta(days=1)
        if is_business_day(d, holidays):
            remaining -= 1
    return d


def _coerce_date(value):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except (ValueError, TypeError, AttributeError):
        return None


def dispute_timeline(assessment_date, holidays=SA_PUBLIC_HOLIDAYS_2026):
    """Return every dispute step with its deadline date, given the assessment date.

    `assessment_date` is an ISO date string (YYYY-MM-DD) or a date. Returns a
    structured, decision-support timeline - not a legal determination.
    """
    start = _coerce_date(assessment_date)
    if start is None:
        return {"available": False, "reason": "Provide the assessment date as YYYY-MM-DD."}

    steps = []
    for key, label, limit, citation in DISPUTE_STEPS:
        deadline = add_business_days(start, limit, holidays)
        steps.append({
            "key": key,
            "label": label,
            "business_days": limit,
            "deadline": deadline.isoformat(),
            "basis": citation,
        })
    return {
        "available": True,
        "as_of": "SA 2026 (TAA 28/2011 + 2023 dispute rules)",
        "assessment_date": start.isoformat(),
        "steps": steps,
        "note": ("Statutory dispute deadlines in TAA business days (weekends, public holidays and "
                 "16 Dec-15 Jan excluded). The objection clock is the critical one - 80 business days. "
                 "SARS may condone a late objection (up to 30 business days on good cause; up to 3 years "
                 "in exceptional circumstances). 'Pay now, argue later' (s164) still applies unless a "
                 "suspension of payment is granted. Decision-support, not legal advice."),
        "disclaimer": "Verify exact dates and the current public-holiday list with a tax practitioner.",
    }
