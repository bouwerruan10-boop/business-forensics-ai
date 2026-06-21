"""
forensic_scan.py — deterministic anomaly *candidate* detection over extracted
financial/bank text.

Exact-match work (duplicate amounts, round-number prevalence, how many figures
exist at all) is arithmetic, not judgement, so it should never be left to the
LLM to eyeball. This module computes the candidates deterministically and hands
them to the forensic agents (Accounting / Auditor / Fraud) to EXPLAIN and verify.

Everything here is indicative: a repeated amount may be a duplicate payment or a
legitimate recurring charge; round numbers may be fraud or routine reporting in
thousands. The agents are told to treat these as leads, not conclusions.
"""
import re
from collections import Counter

# A money-like token: grouped thousands (1,234,567[.89]) OR a bare 4+ digit run.
# Anchored so we don't slice digits out of the middle of a longer number.
_MONEY = re.compile(r"(?<![\d.])(?:R\s*)?(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d{4,}(?:\.\d{1,2})?)(?![\d])")


def _values(text, floor=1.0):
    """All plausible money values in the text at/above `floor` (and below 1e12)."""
    out = []
    for m in _MONEY.finditer(str(text or "")):
        try:
            v = float(m.group(1).replace(",", ""))
        except (TypeError, ValueError):
            continue
        if floor <= v < 1e12:
            out.append(v)
    return out


def _text(memory):
    return (str(getattr(memory, "uploaded_financial_text", "") or "") + "\n" +
            str(getattr(memory, "uploaded_bank_text", "") or ""))


def find_duplicate_amounts(text, min_repeats=3, floor=1000.0, top=8):
    """Amounts (>= floor) that appear >= min_repeats times — duplicate-payment leads."""
    c = Counter(round(v, 2) for v in _values(text, floor))
    dups = [(a, n) for a, n in c.items() if n >= min_repeats]
    dups.sort(key=lambda kv: (-kv[1], -kv[0]))
    return dups[:top]


def round_number_ratio(text, floor=10000.0):
    """Share of large amounts that are exactly divisible by 1000.

    Returns None when there are too few large figures to say anything.
    """
    vals = _values(text, floor)
    if len(vals) < 10:
        return None
    rnd = sum(1 for v in vals if v % 1000 == 0)
    return round(rnd / len(vals), 3)


def forensic_scan(memory):
    text = _text(memory)
    return {
        "data_points": len(_values(text, floor=1.0)),
        "duplicate_amounts": find_duplicate_amounts(text),
        "round_ratio": round_number_ratio(text),
    }


def forensic_scan_block(memory) -> str:
    """Prompt-injectable block of deterministic anomaly candidates (leads, not findings)."""
    s = forensic_scan(memory)
    lines = ["DETERMINISTIC ANOMALY CANDIDATES (computed exactly from the figures in "
             "the supplied text; treat as LEADS to verify against source documents, "
             "NOT as confirmed findings):"]
    lines.append("- Money figures detected: %d" % s["data_points"])

    dups = s["duplicate_amounts"]
    if dups:
        shown = ", ".join("R%s x%d" % ("{:,.0f}".format(a), n) for a, n in dups)
        lines.append("- Repeated identical amounts (possible duplicate payments OR "
                     "legitimate recurring charges - verify): " + shown)
    else:
        lines.append("- Repeated identical amounts: none above the threshold.")

    rr = s["round_ratio"]
    if rr is None:
        lines.append("- Round-number prevalence: too few large figures to assess.")
    else:
        lines.append("- Round-number prevalence: %.0f%% of large figures are exactly "
                     "round (high prevalence can indicate estimated/fabricated entries "
                     "OR routine reporting in thousands - verify)." % (rr * 100))
    return "\n".join(lines)
