"""
narrative_claims.py - verify the numbers inside Imara's LLM-written narratives.

The user-facing narratives (executive summary, the Situation/Complication/Resolution story,
systemic-theme "combined impact" figures, the quick-wins/strategic-plays narrative, the
implementation roadmap's impact figures, and the market/SA-tax/SA-legal summaries) are
free-text the LLM wrote. This scans them for (a) METRIC claims (gross margin, debtor days, ...) and checks each
against the deterministically-computed ratio, and (b) RAND amounts and checks each against the
report's known computed figures. Each becomes a uniform claim object (claim_contract.py).
Honest by design: a number that can't be traced is `unverified`, never a silent pass; a number
that contradicts the computed ratio is `conflict` (the killer case - an LLM stating 21% margin
when the statements compute 33%). Pure deterministic code; reuses the faithfulness engine.
"""

import math
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
    # Phase 2 — surfaces that were emitting unverified numbers untracked:
    ("Market intelligence", "market_context_summary"),
    ("SA tax summary", "sa_tax_summary"),
    ("SA legal summary", "sa_legal_summary"),
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
    # Phase 2 — the implementation roadmap (list of phase dicts) carries LLM-written
    # impact figures (per-phase expected_impact + per-action impact) that were never checked.
    for i, phase in enumerate(report.get("implementation_roadmap") or []):
        if not isinstance(phase, dict):
            continue
        parts = [str(phase.get("focus", "")), str(phase.get("expected_impact", ""))]
        for act in phase.get("actions") or []:
            if isinstance(act, dict):
                parts.append(str(act.get("action", "")))
                parts.append(str(act.get("impact", "")))
        joined = " ".join(p for p in parts if p)
        if joined.strip():
            texts.append(("Roadmap: " + str(phase.get("phase", i))[:40], joined))
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
                       explanation=explanation, as_of="this analysis", computed=computed, unit=unit)
        claims.append(c)
    return claims


def _currency_claims(text, known):
    """All rand amounts >= R1,000 in `text`, checked against the known computed figures."""
    claims, seen = [], set()
    for m in _CUR_RE.finditer(text):
        amt = _to_amount(m.group(1), m.group(2))
        # finiteness guard: a huge digit run parses to float('inf'), which blows up round() —
        # treat as not-a-figure (mirrors verify_finding_figures).
        if amt is None or not math.isfinite(amt) or amt < 1000 or round(amt) in seen:
            continue
        seen.add(round(amt))
        status, explanation, src = verify_currency(amt, known)
        claims.append(make_claim(text=m.group(0).strip(), kind="currency", value=amt,
                                  source=("computed figure: " + src) if src else "LLM narrative",
                                  verification=status, explanation=explanation, as_of="this analysis"))
        if len(claims) >= 12:        # cap per section to avoid flooding
            break
    return claims


# Finding fields that carry LLM-written rand amounts (impact / payoff / cost claims + the
# main `detail` prose — faithfulness checks `detail` for metrics but not for currency).
_FINDING_FIELDS = ("financial_impact", "recommendation", "roi_estimate", "cost_of_inaction", "detail")


def _iter_findings(report):
    """Yield each serialised finding dict from the report once (de-duplicated by title).
    Prefers the complete `department_findings`; falls back to the ranked/quick-win lists."""
    seen, buckets = set(), []
    dept = report.get("department_findings")
    if isinstance(dept, dict):
        for lst in dept.values():
            if isinstance(lst, list):
                buckets.extend(lst)
    if not buckets:
        for key in ("all_findings_ranked", "quick_wins"):
            v = report.get(key)
            if isinstance(v, list):
                buckets.extend(v)
    for f in buckets:
        if not isinstance(f, dict):
            continue
        title = str(f.get("title", ""))
        if title in seen:
            continue
        seen.add(title)
        yield f


def verify_finding_figures(report) -> dict:
    """Check the rand amounts inside each finding's impact / recommendation / ROI /
    cost-of-inaction fields against the report's computed figures. Pure / deterministic.
    These are mostly forward projections, so most are honestly `unverified` (an estimate),
    never a silent pass; one that matches a computed figure is `verified`."""
    if not isinstance(report, dict):
        return {"available": False, "claims": [], "summary": {}}
    known = _known_figures(report)
    claims = []
    for f in _iter_findings(report):
        title = str(f.get("title", ""))[:60]
        seen_amts = set()          # dedup per FINDING, so the same amount in detail + impact = one claim
        for field in _FINDING_FIELDS:
            text = f.get(field)
            if not isinstance(text, str) or not text.strip():
                continue
            for m in _CUR_RE.finditer(text):
                amt = _to_amount(m.group(1), m.group(2))
                # finiteness guard: a huge run of digits parses to float('inf'),
                # which would blow up round()/int() — treat as not-a-figure.
                if amt is None or not math.isfinite(amt) or amt < 1000 or round(amt) in seen_amts:
                    continue
                seen_amts.add(round(amt))
                status, explanation, src = verify_currency(amt, known)
                claims.append(make_claim(
                    text=(title + " - " + m.group(0).strip())[:300], kind="currency", value=amt,
                    source=("computed figure: " + src) if src else "LLM finding (" + field + ")",
                    verification=status, explanation=explanation, as_of="this analysis"))
                if len(claims) >= _MAX_CLAIMS:
                    break
            if len(claims) >= _MAX_CLAIMS:
                break
        if len(claims) >= _MAX_CLAIMS:
            break
    verified = sum(1 for c in claims if c["verification"] == "verified")
    unverified = sum(1 for c in claims if c["verification"] == "unverified")
    return {
        "available": True,
        "claims": claims,
        "summary": {"checked": len(claims), "verified": verified, "unverified": unverified},
        "note": ("Rand amounts inside each finding's impact / recommendation / ROI / cost-of-inaction / detail, "
                 "checked against Imara's computed figures. Most are forward projections that can't be "
                 "traced to a computed figure -> honestly 'unverified' (an estimate), never a silent pass."),
    }


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
