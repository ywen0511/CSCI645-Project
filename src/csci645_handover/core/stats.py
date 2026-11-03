"""Uncertainty helpers: Wilson intervals and a seed-grouped paired bootstrap over shared case IDs."""

from __future__ import annotations

import math

import numpy as np


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    """Wilson score interval for a binomial proportion (None if n == 0)."""
    if n <= 0:
        return None, None
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, center - half), min(1.0, center + half)


def paired_bootstrap_diff(
    a: np.ndarray, b: np.ndarray, n_boot: int = 10000, seed: int = 645, alpha: float = 0.05
) -> dict:
    """Difference of mean outcome ``mean(a) - mean(b)`` with a two-level paired bootstrap.

    Args:
        a, b: arrays of shape (S_a, C) and (S_b, C): rows are training seeds (one row for a deterministic
            controller), columns are the *same* case IDs in the same order.
        Resampling: each replicate draws S rows with replacement independently for each method (seed level;
        a single-row method is never duplicated into fake seed variance), and one shared draw of C case
        columns (case level, paired across methods).
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.ndim == 1:
        a = a[None]
    if b.ndim == 1:
        b = b[None]
    if a.shape[1] != b.shape[1]:
        raise ValueError("Methods must share the same case columns")
    rng = np.random.default_rng(seed)
    sa, sb, c = a.shape[0], b.shape[0], a.shape[1]
    point = float(a.mean() - b.mean())
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        cols = rng.integers(0, c, size=c)
        ra = rng.integers(0, sa, size=sa) if sa > 1 else np.zeros(1, dtype=int)
        rb = rng.integers(0, sb, size=sb) if sb > 1 else np.zeros(1, dtype=int)
        diffs[i] = a[np.ix_(ra, cols)].mean() - b[np.ix_(rb, cols)].mean()
    lo, hi = np.quantile(diffs, [alpha / 2, 1 - alpha / 2])
    return {
        "diff": point, "ci_low": float(lo), "ci_high": float(hi),
        "p_two_sided_sign": float(min(1.0, 2 * min((diffs <= 0).mean(), (diffs >= 0).mean()))),
        "n_boot": n_boot, "bootstrap_seed": seed, "n_cases": c, "seeds_a": sa, "seeds_b": sb,
        "resampling": "training seeds (within method, with replacement) x shared case IDs (paired)",
    }
