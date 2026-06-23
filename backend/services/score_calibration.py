"""
Score calibration — maps the (heuristic, AHP-weighted) Imara Score to a calibrated
probability-of-distress once real outcome labels exist. Platt (logistic) scaling,
pure Python.

Cold-start honest: the AHP-derived band mapping is the EXPERT PRIOR and stands until
there are enough labelled outcomes; `calibrate()` returns {calibrated: False} with the
reason until the threshold is met (a Bayesian-style update of the prior as data arrives).

Two dimensions of validation (kept distinct, per credit-scorecard practice):
  - DISCRIMINATION (does the score RANK good vs bad?) -> services/validation.py (AUC/Gini/KS).
  - CALIBRATION   (is the PROBABILITY right?)        -> calibration_metrics() here
    (calibration-in-the-large, calibration slope, reliability curve, Brier skill).
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


def _logit(p):
    p = min(1 - 1e-6, max(1e-6, p))
    return math.log(p / (1 - p))


def _calibration_slope(pds, labels, iters=2000, lr=0.3):
    """Regress outcome on the logit of the predicted PD: logit(P(bad)) = b0 + slope*logit(pd).
    slope == 1.0 => predictions move with reality 1:1 (well-calibrated spread);
    < 1 => over-confident (too spread out), > 1 => under-confident."""
    xs = [_logit(p) for p in pds]
    ys = [float(l) for l in labels]
    b0 = slope = 0.0
    n = len(xs)
    for _ in range(iters):
        g0 = gs = 0.0
        for x, y in zip(xs, ys):
            e = _sigmoid(b0 + slope * x) - y
            g0 += e
            gs += e * x
        b0 -= lr * g0 / n
        slope -= lr * gs / n
    return slope, b0


def _reliability_curve(pds, labels, bins=(0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.01)):
    """Predicted vs observed per PD bin — the data behind a reliability plot.
    Well-calibrated => mean_predicted ~= observed_bad_rate in each bin."""
    out = []
    for lo, hi in zip(bins, bins[1:]):
        grp = [(p, int(l)) for p, l in zip(pds, labels) if lo <= p < hi]
        if grp:
            mp = sum(p for p, _ in grp) / len(grp)
            ob = sum(l for _, l in grp) / len(grp)
            out.append({"bin": "{:.0%}-{:.0%}".format(lo, min(hi, 1.0)),
                        "n": len(grp), "mean_predicted": round(mp, 3),
                        "observed_bad_rate": round(ob, 3)})
    return out


def calibration_metrics(scores, labels, a, b):
    """Calibration dimension (distinct from discrimination/AUC): is the PROBABILITY right,
    not just the ranking. Returns calibration-in-the-large, slope, reliability curve, and
    Brier vs a prevalence baseline. Pure deterministic."""
    pds = [calibrated_pd(s, a, b) for s in scores]
    n = len(labels)
    observed = sum(labels) / n
    mean_pd = sum(pds) / n
    prevalence_brier = observed * (1 - observed)
    model_brier = _brier(scores, labels, a, b)
    slope, intercept = _calibration_slope(pds, labels)
    return {
        "calibration_in_the_large": {
            "mean_predicted_pd": round(mean_pd, 3),
            "observed_bad_rate": round(observed, 3),
            "difference": round(mean_pd - observed, 3),
            "note": "Close to 0 => the average predicted risk matches reality.",
        },
        "calibration_slope": round(slope, 3),
        "calibration_intercept": round(intercept, 3),
        "slope_note": "1.0 ideal; <1 over-confident, >1 under-confident.",
        "reliability_curve": _reliability_curve(pds, labels),
        "brier": round(model_brier, 4),
        "brier_baseline_prevalence": round(prevalence_brier, 4),
        "brier_skill_score": round(1 - model_brier / prevalence_brier, 3) if prevalence_brier else None,
        "brier_note": "Brier skill score > 0 => better than predicting the base rate for everyone.",
    }


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
        "calibration": calibration_metrics(scores, labels, a, b),
        "note": ("Platt-calibrated probability-of-distress from the Imara Score; refit as more "
                 "outcomes arrive (Bayesian update over the AHP-prior band mapping). "
                 "Discrimination (does it rank?) is at /api/admin/validation; calibration "
                 "(is the probability right?) is the `calibration` block here — both matter."),
    }
