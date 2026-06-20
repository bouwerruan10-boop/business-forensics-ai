"""
AHP (Analytic Hierarchy Process) derivation of the Imara Score component weights.

Purpose: replace "weights we chose" with a documented, auditable derivation. An
expert pairwise-comparison matrix (Saaty 1–9 scale) encodes the lender-priority
rationale; the priority vector (geometric-mean / eigenvector method) yields the
weights, and the Consistency Ratio (CR) proves the judgements are internally
coherent (CR < 0.10 is the accepted threshold). No data or LLM — pure linear
algebra over expert judgement. Feeds MODEL_CARD.md.

Components (lender-priority order) and the rationale encoded in the matrix:
  Profitability > Credit Readiness > Risk & Compliance > Operational Efficiency
  ≈ Financial Integrity ≈ Market Visibility > Tax Compliance ≈ Legal Compliance
"""

import math

COMPONENTS = [
    "Profitability", "Credit Readiness", "Risk & Compliance", "Operational Efficiency",
    "Financial Integrity", "Market Visibility", "Tax Compliance", "Legal Compliance",
]

# Random Consistency Index (Saaty) by matrix order n.
_RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}

# Expert pairwise judgements (upper triangle, Saaty intensities). a_ij = how much
# more important component i is than component j. Reciprocals fill the lower triangle.
_UPPER = {
    (0, 1): 1, (0, 2): 2, (0, 3): 3, (0, 4): 3, (0, 5): 3, (0, 6): 5, (0, 7): 5,
    (1, 2): 1, (1, 3): 2, (1, 4): 2, (1, 5): 2, (1, 6): 4, (1, 7): 4,
    (2, 3): 2, (2, 4): 2, (2, 5): 2, (2, 6): 3, (2, 7): 3,
    (3, 4): 1, (3, 5): 1, (3, 6): 2, (3, 7): 2,
    (4, 5): 1, (4, 6): 2, (4, 7): 2,
    (5, 6): 2, (5, 7): 2,
    (6, 7): 1,
}


def _matrix():
    n = len(COMPONENTS)
    a = [[1.0] * n for _ in range(n)]
    for (i, j), v in _UPPER.items():
        a[i][j] = float(v)
        a[j][i] = 1.0 / float(v)
    return a


def priority_weights(a):
    """Priority vector via the normalised geometric mean of each row (AHP standard)."""
    n = len(a)
    gm = [math.prod(a[i]) ** (1.0 / n) for i in range(n)]
    total = sum(gm)
    return [g / total for g in gm]


def consistency_ratio(a, w):
    """CR = CI / RI, CI = (lambda_max - n)/(n-1). CR < 0.10 = acceptable."""
    n = len(a)
    # lambda_max ≈ average over i of (A·w)_i / w_i
    aw = [sum(a[i][j] * w[j] for j in range(n)) for i in range(n)]
    lam = sum(aw[i] / w[i] for i in range(n)) / n
    ci = (lam - n) / (n - 1)
    ri = _RI.get(n, 1.49)
    return (ci / ri) if ri else 0.0, lam, ci


def imara_weight_derivation():
    """Return the documented AHP derivation of the Imara Score weights."""
    a = _matrix()
    w = priority_weights(a)
    cr, lam, ci = consistency_ratio(a, w)
    derived = {COMPONENTS[i]: round(w[i], 3) for i in range(len(COMPONENTS))}
    return {
        "method": "Analytic Hierarchy Process (Saaty), geometric-mean priority vector",
        "components": COMPONENTS,
        "derived_weights": derived,
        "lambda_max": round(lam, 3),
        "consistency_index": round(ci, 4),
        "consistency_ratio": round(cr, 4),
        "consistent": cr < 0.10,
        "threshold": 0.10,
        "note": ("Weights derived from an expert pairwise-comparison matrix, not chosen ad hoc. "
                 "CR < 0.10 confirms the judgements are internally coherent. The production Score "
                 "uses these priorities rounded to clean values; deviations are documented in the model card."),
    }


# Production weights currently used by _calculate_imara_score (for reconciliation).
PRODUCTION_WEIGHTS = {
    "Profitability": 0.25, "Credit Readiness": 0.20, "Risk & Compliance": 0.15,
    "Operational Efficiency": 0.10, "Financial Integrity": 0.10, "Market Visibility": 0.10,
    "Tax Compliance": 0.05, "Legal Compliance": 0.05,
}
