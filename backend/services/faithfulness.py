"""
Faithfulness verification — Phase 1 of the improvement plan.

LLM agents can cite plausible-but-wrong figures (the live test showed an agent
claiming a 21.3% gross margin when the real, computed value was 33.2%). This
module cross-checks each finding's claimed METRIC against the value the
deterministic ratio engine computed from the actual statements, and flags any
that conflict. It only checks claims it can verify; everything else is left
untouched. Pure functions, no API, fully unit-testable.
"""
import re

# Finding phrase -> (ratio key, unit). Order matters: more specific first.
_METRICS = [
    ("gross margin",            "gross_margin",     "%"),
    ("net profit margin",       "net_margin",       "%"),
    ("net margin",              "net_margin",       "%"),
    ("operating margin",        "operating_margin", "%"),
    ("ebit margin",             "operating_margin", "%"),
    ("current ratio",           "current_ratio",    "x"),
    ("quick ratio",             "quick_ratio",      "x"),
    ("acid test",               "quick_ratio",      "x"),
    ("debtor days",             "debtor_days",      "days"),
    ("days sales outstanding",  "debtor_days",      "days"),
    ("receivable days",         "debtor_days",      "days"),
    ("creditor days",           "creditor_days",    "days"),
    ("days payable",            "creditor_days",    "days"),
    ("payable days",            "creditor_days",    "days"),
    ("inventory days",          "inventory_days",   "days"),
    ("stock days",              "inventory_days",   "days"),
    ("debt-to-equity",          "debt_to_equity",   "x"),
    ("debt to equity",          "debt_to_equity",   "x"),
    ("gearing",                 "debt_to_equity",   "x"),
    ("interest cover",          "interest_coverage","x"),
    ("interest coverage",       "interest_coverage","x"),
]

# Public alias so prose_verifier reuses the same metric vocabulary (no duplication).
METRIC_PHRASES = _METRICS

# A number, optionally preceded by ~ and with a %/x/days suffix.
_NUM_NEAR = re.compile(r"[~≈]?\s*(\d+(?:[.,]\d+)?)\s*(%|x|×|days|day)?", re.IGNORECASE)


def _first_number_after(text_low: str, start: int, window: int = 36):
    """First numeric value appearing within `window` chars after `start`."""
    seg = text_low[start:start + window]
    m = _NUM_NEAR.search(seg)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def _conflicts(claimed: float, computed: float, unit: str) -> bool:
    """Tolerance per metric type. True if the two values materially disagree."""
    if computed is None or claimed is None:
        return False
    diff = abs(claimed - computed)
    rel = diff / max(abs(computed), 1e-9)
    if unit == "%":
        return diff > 2.0 and rel > 0.15          # >2pp AND >15% relative
    if unit == "days":
        return diff > 10.0 and rel > 0.15         # >10 days AND >15% relative
    return diff > 0.2 and rel > 0.15              # ratios (x)


def verify_findings(findings, ratios: dict) -> dict:
    """Annotate findings in place with .verification / .verification_note by
    comparing claimed metrics to the computed ratios. Returns a summary dict."""
    ratios = ratios or {}
    checked = confirmed = conflict = 0
    conflict_titles = []

    for f in findings:
        text = " ".join([getattr(f, "title", "") or "",
                         getattr(f, "detail", "") or "",
                         getattr(f, "benchmark_reference", "") or ""])
        low = text.lower()
        best = None  # (metric_key, unit, claimed, computed)
        for phrase, key, unit in _METRICS:
            if key not in ratios:
                continue
            computed = ratios[key].get("value")
            if computed is None:
                continue
            idx = low.find(phrase)
            if idx == -1:
                continue
            claimed = _first_number_after(low, idx + len(phrase))
            if claimed is None:
                continue
            best = (key, unit, claimed, computed, ratios[key].get("label", key))
            break  # first verifiable metric per finding is enough

        if not best:
            continue
        key, unit, claimed, computed, label = best
        checked += 1
        u = "" if unit in ("x",) else unit
        if _conflicts(claimed, computed, unit):
            conflict += 1
            f.verification = "conflict"
            f.verification_note = (
                "Computed {} is {}{} from the statements (finding states ~{}{}).".format(
                    label, _fmt(computed), u, _fmt(claimed), u))
            conflict_titles.append(getattr(f, "title", ""))
        else:
            confirmed += 1
            f.verification = "confirmed"
            f.verification_note = "Matches computed {} ({}{}).".format(label, _fmt(computed), u)

    return {
        "checked": checked,
        "confirmed": confirmed,
        "conflicts": conflict,
        "conflict_titles": conflict_titles[:10],
    }


def _fmt(v):
    if v is None:
        return "n/a"
    return ("%g" % round(v, 2))
