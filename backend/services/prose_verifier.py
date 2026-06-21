"""
prose_verifier.py - deterministic narrative-consistency check (Tier 1.1).

faithfulness.py guards the NUMBERS: it catches a finding that cites a wrong
figure (claims a 21.3% gross margin when the computed value is 33.2%). The
remaining anti-hallucination gap is QUALITATIVE: an LLM narrative can describe a
metric with a health adjective that contradicts the metric's deterministically
computed state WITHOUT misstating any number - e.g. calling a current ratio
"comfortable" when the ratio engine flagged it "critical", or a margin "weak"
when the engine flagged it "good". This module flags exactly those directional
contradictions.

Design choices that keep it HIGH-CONFIDENCE / LOW-FALSE-POSITIVE (the plan calls
this "small, high-confidence, low-risk"):
  * It reuses the SAME metric phrase map as faithfulness (no duplication).
  * It uses ONLY direction-independent, health-valenced adjectives. Magnitude
    words (low/high/thin/ample) are deliberately EXCLUDED because their valence
    flips by metric ("low gearing" is good, "low current ratio" is bad);
    health words ("healthy/strong/strained/weak") assert the overall state and
    do not flip.
  * GRAMMATICAL ADJACENCY, not mere proximity: the adjective only counts if it is
    connected to the metric phrase by an uninterrupted run of CONNECTOR tokens
    (articles, copulas, adverbs, numbers) - e.g. "comfortable current ratio" or
    "current ratio of 0.4x is comfortable". A conjunction, punctuation, or any
    other content word BETWEEN the adjective and the phrase is a hard boundary,
    so "strong leadership team and a current ratio of 0.4x" does NOT flag (the
    adjective modifies "leadership team", not the ratio). This was added after a
    pressure test surfaced exactly that false positive.
  * It flags ONLY the two unambiguous cross cases: a positive health word about a
    metric rated "critical", or a negative health word about a metric rated
    "good". The middle state ("warning") is never flagged. A negation
    ("not strong", "is not comfortable") suppresses the flag.

Pure functions, no API call, fully unit-testable. Nothing here changes the Imara
Score - it only annotates findings, mirroring faithfulness.
"""
import re

# Reuse faithfulness's phrase -> (ratio key, unit) map so the two verifiers stay
# in lock-step and we don't duplicate the metric vocabulary.
from services.faithfulness import METRIC_PHRASES

# Direction-INDEPENDENT health adjectives (single tokens only - see docstring).
_POSITIVE = {
    "healthy", "strong", "robust", "solid", "comfortable", "sound", "excellent",
    "favourable", "favorable", "reassuring", "resilient", "well-managed", "good",
}
_NEGATIVE = {
    "weak", "poor", "strained", "distressed", "concerning", "alarming", "worrying",
    "worrisome", "unhealthy", "precarious", "fragile", "troubling", "inadequate",
    "deteriorating", "dire", "weakening",
}

# Tokens that may sit BETWEEN the metric phrase and its modifying adjective
# without breaking the grammatical attachment (articles, copulas, hedges, adverbs).
_CONNECTORS = {
    "a", "an", "the", "its", "their", "our", "of", "at", "is", "are", "was", "were",
    "be", "been", "remains", "remain", "stays", "stay", "looks", "look", "appears",
    "appear", "sits", "sit", "seems", "seem", "stands", "stand", "very", "quite",
    "rather", "somewhat", "fairly", "pretty", "still", "currently", "now", "really",
    "generally", "broadly", "relatively", "reasonably", "particularly", "especially",
    "remarkably", "notably", "around", "about", "approximately", "roughly", "circa",
}
_NEGATORS = {"not", "never", "no", "hardly", "barely", "isn't", "aren't", "wasn't",
             "weren't", "isnt", "arent", "nor", "without", "n't"}
# Conjunctions that join the phrase to a DIFFERENT clause/subject -> hard boundary.
_BOUNDARY_WORDS = {"and", "but", "while", "whereas", "however", "though", "although",
                   "yet", "separately", "meanwhile", "conversely", "despite", "whilst",
                   "plus", "also", "because", "since", "as", "with", "for"}
_BOUNDARY_PUNCT = set(",;:.!?()")
_NUMERIC = re.compile(r"^[r$£€]?[\d][\d.,]*(x|%|bps)?$", re.I)


def _parse(raw):
    """Return (bareword, is_punct_boundary). Only TRAILING clause punctuation (or
    an internal ; : ( )) is a boundary - an internal '.' or ',' inside a number
    (e.g. "0.4x", "1,250") must NOT be treated as a clause break."""
    core = raw.strip("'\"()")
    trailing = bool(core) and core[-1] in ",;:.!?"
    internal_hard = any(c in raw for c in ";:()")
    w = core.rstrip(",;:.!?").lower()
    return w, (trailing or internal_hard)


def _is_connector(w):
    return w in _CONNECTORS or bool(_NUMERIC.match(w))


def _scan(tokens, polarity_set):
    """Scan tokens ordered NEAREST->FARTHEST from the metric phrase. Return the
    matched polarity word if a health adjective is grammatically adjacent and not
    negated, else None."""
    negated = False
    cand = None
    for raw in tokens:
        if not raw:
            continue
        w, punct_boundary = _parse(raw)
        if cand is None:
            if w in _NEGATORS:
                negated = True
                continue
            if w in polarity_set:
                cand = w
                # keep scanning outward only to detect a preceding negator
                continue
            if _is_connector(w):          # numbers / articles / copulas first
                continue
            if punct_boundary or w in _BOUNDARY_WORDS:
                return None
            return None   # a different content word -> no adjacency
        else:
            if w in _NEGATORS:
                return None
            if punct_boundary or w in _BOUNDARY_WORDS or not _is_connector(w):
                break     # candidate stands
    return None if (cand is None or negated) else cand


def _finding_text(f):
    return " ".join([
        getattr(f, "title", "") or "",
        getattr(f, "detail", "") or "",
        getattr(f, "benchmark_reference", "") or "",
    ])


def verify_prose(findings, ratios):
    """Annotate findings in place with .prose_check / .prose_note where a
    qualitative health-claim is grammatically attached to a metric whose computed
    status contradicts it. Returns a summary. Conservative: <=1 flag per finding."""
    ratios = ratios or {}
    checked = flagged = 0
    flag_titles = []

    for f in findings:
        text_low = _finding_text(f).lower()
        if not text_low.strip():
            continue

        flagged_this = False
        for phrase, key, _unit in METRIC_PHRASES:
            if flagged_this:
                break
            r = ratios.get(key)
            if not isinstance(r, dict):
                continue
            status = (r.get("status") or "").lower()
            if status not in ("good", "critical"):
                continue
            if r.get("value") is None:
                continue

            want = _NEGATIVE if status == "good" else _POSITIVE

            start = 0
            while True:
                idx = text_low.find(phrase, start)
                if idx == -1:
                    break
                start = idx + len(phrase)
                left_tokens = list(reversed(text_low[:idx].split()))
                right_tokens = text_low[idx + len(phrase):].split()
                hit = _scan(left_tokens, want) or _scan(right_tokens, want)
                if not hit:
                    continue

                checked += 1
                flagged += 1
                flagged_this = True
                label = r.get("label", key)
                rated = "healthy (status: good)" if status == "good" else "a concern (status: critical)"
                f.prose_check = "conflict"
                f.prose_note = (
                    "Narrative calls {} \"{}\" but the computed {} is rated {} from the "
                    "statements - reconcile the wording.".format(label, hit, label, rated))
                flag_titles.append(getattr(f, "title", ""))
                break

    return {"checked": checked, "flagged": flagged, "flag_titles": flag_titles[:10]}
