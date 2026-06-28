"""
narrative_claims.py - verify the numbers inside Imara's LLM-written narratives.

The most-read outputs (executive summary, the Situation/Complication/Resolution story,
systemic-theme "combined impact" figures, the quick-wins narrative) are free-text the LLM
wrote. This scans them for (a) METRIC claims (gross margin, debtor days, ...) and checks each
against the deterministically-computed ratio, and (b) RAND amounts and checks each against the
report's known computed figures. Each becomes a uniform claim object (claim_contract.py).
Honest by design: a number that can't be traced is `unverified`, never a silent pass; a number
that contradicts the computed ratio is `conflict` (the killer case - an LLM stating 21% margin
when the statements compute 33%). Pure deterministic code; reuses the faithfulness engine.
"""

import re

from services.faithfulness import _METRICS, _first_number_after
from services.claim_contract import make_claim, verify_metric, verify_currency

# narrative report keys to scan (label, key)
_NARRATIVE_KEYS = (
    ("Executive summary", "executive_summary"),
    ("Situation", "situation"),
    ("Complication", "complication"),
    ("Resolution", "resolution"),
    ("Quick-wins narrative", "quick_wins_narrative"),
    ("Strategic plays narrative", "strategic_plays_narrative"),
)

_CUR_RE = re.compile(r"R\s?(\d[\d  ,\.]*\d|\d)\s*(million|billion|bn|m|k)?", re.IGNORECASE)
_MAX_CLAIMS = 200


def _to_amount(num, suffix):
    """Parse a rand amount token (+ optional million/k suffix) to float."""
    t = re.sub(r"[\s ]", "", str(num))
    if "," in t and "." in t:
        dec = "," if t.rfind(",") > t.rfind(".") else "."
        t = t.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "," in t:
        t = t.replace(",", ".") if re.search(r",\d{1,2}$", t) else t.replace(",", "")
    try:
        v = float(t)
    except ValueError:
        return None
    s = (suffix or "").lower()
    if s in ("million", "m"):
        v *= 1_000_000
    elif s in ("billion", "bn"):
        v *= 1_000_000_000
    elif s == "k":
        v *= 1_000
    return v


def _known_figures(report):
    """The computed/profile figures a narrative rand-amount can legitimately match."""
    out = {}
    figs = report.get("financial_figures")
    if isinstance(figs, dict):
        for k, v in figs.items():
            if isinstance(v, (int, float)):
                out[str(k)] = float(v)
    for k in ("annual_revenue",):
        v = report.get(k)
        if isinstance(v, (int, float)) and v:
            out[k] = float(v)
    return out


def _section_texts(report):
    texts = []
    for label, key in _NARRATIVE_KEYS:
        t = report.get(key)
        if isinstance(t, str) and t.strip():
            texts.append((label, t))
    for i, theme in enumerate(report.get("systemic_themes") or []):
        if isinstance(theme, dict):
            parts = " ".join(str(theme.get(k, "")) for k in ("title", "narrative", "combined_impact"))
            if parts.strip():
                texts.append(("Systemic theme: " + str(theme.get("title", i))[:40], parts))
    return texts


def _metric_claims(text, ratios):
    """All metric phrases present in `text` with a stated number, verified vs computed."""
    low = text.lower()
    claims, seen = [], set()
    for phrase, key, unit in _METRICS:
        if key not in ratios or key in seen:
            continue
        r = ratios.get(key) or {}
        computed = r.get("value")
        if computed is None:
            continue
        idx = low.find(phrase)
        if idx == -1:
            continue
        claimed = _first_number_after(low, idx + len(phrase))
        if claimed is None:
            continue
        seen.add(key)
        label = r.get("label", key)
        status, explanation = verify_metric(claimed, computed, unit, label)
        c = make_claim(text=phrase + " ~" + str(claimed), kind="metric", value=claimed,
                       source="computed ratio: " + str(key), verification=status,
                       explanation=explanation, as_of="this analysis")
        claims.append(c)
    return claims


def _currency_claims(text, known):
    """All rand amounts >= R1,000 in `text`, checked against the known computed figures."""
    claims, seen = [], set()
    for m in _CUR_RE.finditer(text):
        amt = _to_amount(m.group(1), m.group(2))
        if amt is None or amt < 1000 or round(amt) in seen:
            continue
        seen.add(round(amt))
        status, explanation, src = verify_currency(amt, known)
        claims.append(make_claim(text=m.group(0).strip(), kind="currency", value=amt,
                                  source=("computed figure: " + src) if src else "LLM narrative",
                                  verification=status, explanation=explanation, as_of="this analysis"))
        if len(claims) >= 12:        # cap per section to avoid flooding
            break
    return claims


def verify_narrative(report) -> dict:
    """Scan the report's narratives, verify every number, return the claim list + summary."""
    if not isinstance(report, dict):
        return {"available": False, "claims": [], "summary": {}}
    ratios = report.get("financial_ratios") if isinstance(report.get("financial_ratios"), dict) else {}
    known = _known_figures(report)

    claims = []
    by_section = {}
    for label, text in _section_texts(report):
        sect = _metric_claims(text, ratios) + _currency_claims(text, known)
        for c in sect:
            c["section"] = label
        claims.extend(sect)
        agg = by_section.setdefault(label, {"verified": 0, "conflict": 0, "unverified": 0})
        for c in sect:
            agg[c["verification"]] = agg.get(c["verification"], 0) + 1
        if len(claims) >= _MAX_CLAIMS:
            break

    verified = sum(1 for c in claims if c["verification"] == "verified")
    conflicts = sum(1 for c in claims if c["verification"] == "conflict")
    unverified = sum(1 for c in claims if c["verification"] == "unverified")
    return {
        "available": True,
        "claims": claims,
        "summary": {"total": len(claims), "verified": verified, "conflicts": conflicts,
                    "unverified": unverified, "by_section": by_section},
        "note": ("Numbers found in the narrative text, each checked against Imara's deterministically-computed "
                 "values. 'conflict' = the narrative disagrees with the computed figure; 'unverified' = the number "
                 "could not be traced to a computed figure (treat as an estimate). Decision-support only."),
    }
