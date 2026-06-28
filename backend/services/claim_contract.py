"""
claim_contract.py - the uniform claim/evidence object for Imara's "prove it" discipline.

Every user-facing assertion is normalised to one shape: what was claimed, the source it
rests on, a verification status, an explanation of WHY (the computed value it matches or
why it can't be checked), and a date. Honest by design: a claim that cannot be checked is
`unverified`, NEVER a fabricated pass. The verifiers here are pure deterministic code (they
reuse the faithfulness tolerance engine) - the LLM is never asked to grade itself.

verification: "verified" (matches a computed/authoritative source) | "conflict" (materially
disagrees with the computed source) | "unverified" (no source to check against).
"""

from services.faithfulness import _conflicts, _METRICS

KINDS = ("metric", "currency", "count", "status", "qualitative")

# ratio_key -> unit (derived from the faithfulness metric vocabulary; single source of truth)
KEY_UNIT = {key: unit for _phrase, key, unit in _METRICS}


def _fmt(v, unit=""):
    if v is None:
        return "n/a"
    v = round(float(v), 2)
    if unit == "%":
        return ("%g%%" % v)
    if unit == "days":
        return ("%g days" % round(v, 1))
    if unit == "x":
        return ("%gx" % v)
    return ("%g" % v)


def grade_confidence(status, claimed=None, computed=None, unit=""):
    """Deterministic confidence (0-1 float) + band for a claim — the calibrated upgrade
    of the verified/conflict/unverified flag. Honest by construction: a `verified` claim
    is high (tightened toward 1.0 when the stated value nearly equals the computed one);
    a `conflict` is low (we are confident it is WRONG); an `unverified` estimate is low
    (it can be neither confirmed nor refuted). Never invents precision it doesn't have —
    the closeness term is only applied when both numbers are present.
    Returns (score, band) where band is high (>=0.75) | medium (>=0.45) | low."""
    if status == "verified":
        score = 0.90
        if claimed is not None and computed is not None:
            try:
                rel = abs(float(claimed) - float(computed)) / max(abs(float(computed)), 1e-9)
            except (TypeError, ValueError):
                rel = None
            if rel is not None:
                score = 0.97 if rel <= 0.005 else 0.90 if rel <= 0.05 else 0.82
    elif status == "conflict":
        score = 0.15
    else:                                   # unverified (or unknown) -> treat as estimate
        score = 0.35
    band = "high" if score >= 0.75 else "medium" if score >= 0.45 else "low"
    return round(score, 2), band


def make_claim(text, kind, value=None, source="", verification="unverified",
               explanation="", as_of="", confidence=None, computed=None, unit="") -> dict:
    """Normalise one assertion into the uniform claim object. If `confidence` is not
    supplied it is graded deterministically from the verification status (and the
    claimed-vs-computed closeness when `computed` is given)."""
    status = verification if verification in ("verified", "conflict", "unverified") else "unverified"
    if confidence is None:
        score, band = grade_confidence(status, value, computed, unit)
    else:
        try:
            score = round(max(0.0, min(1.0, float(confidence))), 2)
        except (TypeError, ValueError):
            score = 0.0
        band = "high" if score >= 0.75 else "medium" if score >= 0.45 else "low"
    return {
        "text": str(text or "")[:300],
        "kind": kind if kind in KINDS else "qualitative",
        "value": value,
        "source": str(source or ""),
        "verification": status,
        "explanation": str(explanation or ""),
        "as_of": str(as_of or ""),
        "confidence": score,
        "confidence_band": band,
    }


def verify_metric(claimed, computed, unit, label="value"):
    """Verify a claimed metric value against the computed ratio. Returns (status, explanation)."""
    if computed is None or claimed is None:
        return "unverified", "No computed {} to check against.".format(label)
    if _conflicts(claimed, computed, unit):
        return "conflict", "Computed {} is {} from the statements (stated ~{}).".format(
            label, _fmt(computed, unit), _fmt(claimed, unit))
    return "verified", "Matches the computed {} ({}).".format(label, _fmt(computed, unit))


def verify_currency(claimed, known_figures, rel_tol=0.02):
    """Verified if the claimed rand amount matches a computed figure within tolerance.
    `known_figures` is {source_label: value}. Returns (status, explanation, source)."""
    if claimed is None:
        return "unverified", "No amount parsed.", ""
    for src, val in (known_figures or {}).items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if v and abs(claimed - v) <= max(1.0, abs(v) * rel_tol):
            return "verified", "Matches the computed {} (R{:,.0f}).".format(src, v), src
    return "unverified", "Not traceable to a computed figure in this report - treat as an estimate.", ""
