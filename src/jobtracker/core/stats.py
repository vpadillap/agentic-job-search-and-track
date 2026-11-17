"""Small, dependency-free statistics for one person's job-search outcomes.

Rates are shrunk toward the overall rate (Beta prior), so a 1-of-1 group does
not show 100%. Intervals are Beta credible intervals. The prediction model is a
recency-weighted, L2-regularized logistic regression fitted by gradient
descent; with a few dozen cases that is all the data can support.
"""
from __future__ import annotations

import math
import random

PRIOR_WEIGHT = 4.0       # pseudo-cases of the overall rate added to every group
INTERVAL = 0.80          # central credible interval shown to the user


# ── Beta distribution ─────────────────────────────────────────────────────

def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Numerical Recipes)."""
    tiny = 1e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h


def beta_cdf(x: float, a: float, b: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    log_front = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                 + a * math.log(x) + b * math.log(1 - x))
    front = math.exp(log_front)
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1 - x) / b


def beta_quantile(q: float, a: float, b: float) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if beta_cdf(mid, a, b) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def smoothed_rate(successes: int, cases: int, prior_rate: float,
                  prior_weight: float = PRIOR_WEIGHT) -> dict:
    """A rate shrunk toward `prior_rate`, with its credible interval."""
    prior_rate = min(max(prior_rate, 0.01), 0.99)
    a = successes + prior_rate * prior_weight
    b = cases - successes + (1 - prior_rate) * prior_weight
    tail = (1 - INTERVAL) / 2
    return {
        "raw": successes / cases if cases else None,
        "rate": a / (a + b),
        "low": beta_quantile(tail, a, b),
        "high": beta_quantile(1 - tail, a, b),
    }


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


# ── logistic regression ───────────────────────────────────────────────────

def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def fit_logistic(rows: list[dict[str, float]], labels: list[int], weights: list[float],
                 l2: float = 1.0, steps: int = 400, rate: float = 0.5) -> dict:
    """Fit P(label=1 | features). Rows are sparse {feature: value} dicts (one-hot)."""
    features = sorted({f for row in rows for f in row})
    coef = {f: 0.0 for f in features}
    total = sum(weights) or 1.0
    positive = sum(w for w, y in zip(weights, labels, strict=True) if y) / total
    positive = min(max(positive, 0.01), 0.99)
    bias = math.log(positive / (1 - positive))
    for _ in range(steps):
        grad = {f: 0.0 for f in features}
        grad_bias = 0.0
        for row, y, w in zip(rows, labels, weights, strict=True):
            p = _sigmoid(bias + sum(coef[f] * v for f, v in row.items()))
            error = (p - y) * w
            grad_bias += error
            for f, v in row.items():
                grad[f] += error * v
        bias -= rate * grad_bias / total
        for f in features:
            coef[f] -= rate * (grad[f] / total + l2 * coef[f] / total)
    return {"bias": bias, "coef": coef}


def predict(model: dict, row: dict[str, float]) -> float:
    return _sigmoid(model["bias"] + sum(model["coef"].get(f, 0.0) * v for f, v in row.items()))


def contributions(model: dict, row: dict[str, float]) -> list[tuple[str, float]]:
    """How much each present feature moved the prediction (log-odds), largest first."""
    items = [(f, model["coef"].get(f, 0.0) * v) for f, v in row.items()]
    return sorted(items, key=lambda item: abs(item[1]), reverse=True)


def brier(predictions: list[float], labels: list[int]) -> float:
    return sum((p - y) ** 2 for p, y in zip(predictions, labels, strict=True)) / len(labels)


def bootstrap_models(rows: list[dict[str, float]], labels: list[int], weights: list[float],
                     count: int = 20, seed: int = 7) -> list[dict]:
    """Models fitted on resamples, for an uncertainty range around a prediction."""
    rng = random.Random(seed)
    models = []
    n = len(rows)
    for _ in range(count):
        idx = [rng.randrange(n) for _ in range(n)]
        models.append(fit_logistic([rows[i] for i in idx], [labels[i] for i in idx],
                                   [weights[i] for i in idx], steps=200))
    return models
