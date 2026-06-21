"""
Score calibration — maps the (heuristic, AHP-weighted) Imara Score to a calibrated
probability-of-distress once real outcome labels exist. Platt (logistic) scaling,
pure Python.

Cold-start honest: the AHP-derived band mapping is the EXPERT PRIOR and stands until
there are enough labelled outcomes; `calibrate()` returns {calibrated: False} with the
reason until the threshold is met (a Bayesian-style update of the prior as data arrives).
"""
import math


def _sigmoid(z):
    if z < -30:
        return 0.0
    if z > 30:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def fit_platt(scores, labels, iters=3000, lr=0.5):
    """Logistic fit P(bad) = sigmoid(a*(score/100) + b) by gradient descent."""
    xs = [s / 100.0 for s in scores]
    ys = [float(l) for l in labels]
    a = b = 0.0
    n = len(xs)
    for _ in range(iters):
        ga = gb = 0.0
        for x, y in zip(xs, ys):
            e = _sigmoid(a * x + b) - y
            ga += e * x
            gb += e
        a -= lr * ga / n
        b -= lr * gb / n
    return a, b


def calibrated_pd(score, a, b):
    return _sigmoid(a * (score / 100.0) + b)


def _brier(scores, labels, a, b):
    return sum((calibrated_pd(s, a, b) - l) ** 2 for s, l in zip(scores, labels)) / len(scores)


def calibrate(pairs, min_n=50):
    """pairs: [{imara_score, label}] (1=bad). Returns a Platt mapping when there is
    enough data, else {calibrated: False} (the AHP prior band mapping stands)."""
    pairs = [p for p in pairs if p.get("imara_score") is not None and p.get("label") in (0, 1)]
    n = len(pairs)
    n_bad = sum(p["label"] for p in pairs)
    if n < min_n or n_bad == 0 or n_bad == n:
        return {"calibrated": False, "n": n, "n_bad": n_bad,
                "reason": ("Need >= {} labelled cases with both outcomes (have {}, {} bad). "
                           "The AHP-derived band mapping (expert prior) stands until then."
                           ).format(min_n, n, n_bad)}
    scores = [p["imara_score"] for p in pairs]
    labels = [p["label"] for p in pairs]
    a, b = fit_platt(scores, labels)
    return {
        "calibrated": True, "n": n, "n_bad": n_bad,
        "platt_a": round(a, 4), "platt_b": round(b, 4),
        "brier": round(_brier(scores, labels, a, b), 4),
        "example_pd": {str(s): round(calibrated_pd(s, a, b), 3) for s in (20, 40, 60, 80)},
        "note": ("Platt-calibrated probability-of-distress from the Imara Score; refit as more "
                 "outcomes arrive (Bayesian update over the AHP-prior band mapping)."),
    }
