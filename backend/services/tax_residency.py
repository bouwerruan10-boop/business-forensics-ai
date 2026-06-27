"""
tax_residency.py - deterministic SA tax-residency physical-presence test (s1).

Pure functions; the LLM only narrates. SA has TWO residency tests for a natural
person: "ordinarily resident" (a facts-and-circumstances test of where your real
home is - NOT computable, so it is surfaced as a question, never asserted) and the
PHYSICAL-PRESENCE test, which is a pure day-count and IS computable:

  resident by presence if ALL of:
    - more than 91 days in SA in the current year of assessment, AND
    - more than 91 days in SA in EACH of the 5 preceding years, AND
    - more than 915 days in SA in AGGREGATE over those 5 preceding years.
  -> resident from the FIRST day of the current year.

Cessation: a person who is resident on the physical-presence basis ceases to be a
resident once physically OUTSIDE SA for a continuous period of at least 330 full
days. Thresholds come from the dated `sa_rates`. Re-verify against SARS each year.
Decision-support, not a residency ruling; ordinarily-resident can override this.
"""

from services import sa_rates


def _int(v):
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return 0
    return n if n > 0 else 0


def physical_presence_test(current_year_days, prior_years_days, days_continuously_absent=0):
    """Apply the physical-presence test from day-counts.

    `current_year_days`  - days physically in SA in the year under consideration.
    `prior_years_days`   - iterable of days in SA for the 5 preceding years.
    `days_continuously_absent` - longest continuous spell currently OUTSIDE SA.
    """
    cur = _int(current_year_days)
    priors = [_int(d) for d in (prior_years_days or [])][:5]

    cur_ok = cur > sa_rates.PRESENCE_CURRENT_MIN
    each_ok = len(priors) == 5 and all(d > sa_rates.PRESENCE_EACH_PRIOR_MIN for d in priors)
    aggregate = sum(priors)
    agg_ok = aggregate > sa_rates.PRESENCE_AGGREGATE_PRIOR_MIN

    resident = bool(cur_ok and each_ok and agg_ok)
    ceases = _int(days_continuously_absent) >= sa_rates.PRESENCE_CESSATION_DAYS

    prongs = [
        {"prong": "current_year", "label": "More than 91 days this year",
         "met": cur_ok, "value": cur, "threshold": sa_rates.PRESENCE_CURRENT_MIN},
        {"prong": "each_prior_year", "label": "More than 91 days in each of the 5 prior years",
         "met": each_ok, "value": priors, "threshold": sa_rates.PRESENCE_EACH_PRIOR_MIN},
        {"prong": "aggregate_prior", "label": "More than 915 days across the 5 prior years",
         "met": agg_ok, "value": aggregate, "threshold": sa_rates.PRESENCE_AGGREGATE_PRIOR_MIN},
    ]

    if resident and ceases:
        status, summary = "ceased", (
            "You meet the presence test, but a continuous absence of {}+ full days ends residency on the "
            "physical-presence basis - confirm your cessation date and the s9H exit-tax position."
        ).format(sa_rates.PRESENCE_CESSATION_DAYS)
    elif resident:
        status, summary = "resident", (
            "You are a SA tax resident on the physical-presence basis (resident worldwide income applies).")
    else:
        missing = [p["label"] for p in prongs if not p["met"]]
        status, summary = "not_resident_by_presence", (
            "The physical-presence test is NOT met (" + "; ".join(missing) + "). "
            "Note: you can still be 'ordinarily resident' on the facts even if the day-count fails.")

    return {
        "available": True,
        "as_of": "SA 2026/27 (Income Tax Act s1 'resident')",
        "status": status,
        "resident_by_presence": resident,
        "ceases_on_absence": ceases,
        "prongs": prongs,
        "aggregate_prior_days": aggregate,
        "summary": summary,
        "ordinarily_resident_note": ("The 'ordinarily resident' test (where your real, settled home is) "
                                     "OVERRIDES the day-count: if SA is still your true home you remain "
                                     "resident regardless of days. This requires a facts assessment."),
        "disclaimer": ("Decision-support only - not a residency ruling. Formalise any cessation with SARS "
                       "(RAV01) and confirm with a cross-border tax practitioner."),
    }
