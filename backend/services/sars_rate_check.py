"""
sars_rate_check.py - deterministic SARS rate-currency diff engine ("scraper" core).

Pure, no network. Given SARS page text (supplied by the operator, or fetched one URL
at a time by sars_fetch.py), it parses each figure by its stable text label and DIFFS
it against Imara's hardcoded value (the manifest). Output is an ALERT-ONLY report -
{matches, mismatches, unparsed} - for human review. It NEVER edits sa_rates.py: a
scraped value is a prompt to verify, not ground truth. Honest by design: a figure it
cannot locate is reported `unparsed`, never a silent pass (same discipline as the TCS
and statement-integrity checks).

Numbers use Decimal for exact comparison. Re-verify any flagged figure against SARS.
"""

import re
from decimal import Decimal, InvalidOperation

from services.sars_rate_manifest import manifest, PAGES

_PCT_TOL = Decimal("0.01")     # percent match tolerance
_ZAR_TOL = Decimal("0.5")      # rand match tolerance


def _parse_number(s):
    """Parse a SA-formatted numeric token to Decimal (R / spaces / both decimal
    conventions). Returns None on failure."""
    if s is None:
        return None
    t = re.sub(r"[Rr%\s ]", "", str(s).strip())
    if not t:
        return None
    if "," in t and "." in t:                       # last separator is the decimal
        dec = "," if t.rfind(",") > t.rfind(".") else "."
        t = t.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "," in t:                                   # comma decimal only if ",dd" at end
        t = t.replace(",", ".") if re.search(r",\d{1,2}$", t) else t.replace(",", "")
    try:
        return Decimal(t)
    except (InvalidOperation, ValueError):
        return None


def _html_to_text(content):
    """Best-effort HTML -> text; plain text passes through unchanged."""
    s = content if isinstance(content, str) else ""
    if "<" in s and ">" in s:
        try:
            from bs4 import BeautifulSoup
            return BeautifulSoup(s, "lxml").get_text(" ", strip=True)
        except Exception:
            return re.sub(r"<[^>]+>", " ", s)
    return s


def _extract(text, anchors, unit, window=140):
    """Find the value near the first matching anchor. percent -> a `NN%` token;
    zar -> an amount token (handles 'R1 million'). Returns Decimal or None."""
    low = text.lower()
    for a in anchors:
        i = low.find(str(a).lower())
        if i == -1:
            continue
        seg = text[i:i + window]
        if unit == "percent":
            m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", seg)
            if m:
                return _parse_number(m.group(1))
        else:  # zar
            m = re.search(r"R?\s*(\d[\d  ,\.]*\d|\d)\s*(million|m\b)?", seg)
            if m:
                val = _parse_number(m.group(1))
                if val is None:
                    continue
                if m.group(2):                       # 'R1 million' / 'R2.3 million'
                    val = val * Decimal(1_000_000)
                if val >= 100:                       # skip tiny noise (footnote refs etc.)
                    return val
    return None


def diff_against_manifest(page_contents):
    """Core: parse each manifest figure from the supplied page text and diff vs expected.
    `page_contents` maps a SARS page id (see manifest PAGES) -> raw HTML/text. Pure;
    never writes any figure."""
    page_contents = page_contents if isinstance(page_contents, dict) else {}
    text_by_page = {k: _html_to_text(v) for k, v in page_contents.items()}

    matches, mismatches, unparsed = [], [], []
    for e in manifest():
        text = text_by_page.get(e["page"])
        if not text:
            unparsed.append({"key": e["key"], "label": e["label"], "page": e["page"],
                             "reason": "page content not supplied"})
            continue
        found = _extract(text, e["anchors"], e["unit"])
        if found is None:
            unparsed.append({"key": e["key"], "label": e["label"], "page": e["page"],
                             "reason": "value not found near its label"})
            continue
        expected = Decimal(str(e["expected"]))
        tol = _PCT_TOL if e["unit"] == "percent" else _ZAR_TOL
        sane = e["sanity"][0] <= float(found) <= e["sanity"][1]
        row = {"key": e["key"], "label": e["label"], "unit": e["unit"],
               "expected": float(expected), "found": float(found), "in_sanity_range": sane,
               "citation": e["citation"], "sars_url": PAGES.get(e["page"])}
        if abs(found - expected) <= tol:
            matches.append(row)
        else:
            mismatches.append(row)
    return matches, mismatches, unparsed


def check(page_contents) -> dict:
    """Full alert-only rate-currency report from supplied SARS page text."""
    matches, mismatches, unparsed = diff_against_manifest(page_contents)
    checked = len(matches) + len(mismatches)
    if mismatches:
        status = "drift_detected"
    elif checked:
        status = "current"
    else:
        status = "no_values_parsed"
    return {
        "available": True,
        "status": status,
        "summary": {"checked": checked, "matched": len(matches),
                    "drifted": len(mismatches), "unparsed": len(unparsed)},
        "mismatches": mismatches,
        "matches": matches,
        "unparsed": unparsed,
        "note": ("ALERT-ONLY. A 'drift' or 'unparsed' result is a prompt to VERIFY the figure against SARS "
                 "and, if confirmed, update sa_rates.py via a sourced, human-approved change (see "
                 "corpus_refresh.py). This tool never edits any rate. Scraped values are not ground truth."),
        "disclaimer": "Decision-support / ops aid - not tax advice; confirm every figure with SARS.",
    }
