"""Paired, seed-aware v3 effect estimates; no simulator imports."""
from __future__ import annotations

import numpy as np


def paired_effect(a, b, *, repeats=10000, seed=6455401, confidence=0.95):
    """Inputs (training seeds, conditions, base cases), with matched case order.

    A deterministic controller has one row and is broadcast, never resampled as
    fake training seeds. Same-seed learned comparisons use matched seed rows.
    One base-case index draw is shared across conditions, preserving dependence
    between severity levels. Conditions are fixed strata, not sampled units.
    """
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.ndim != 3 or b.ndim != 3 or a.shape[1:] != b.shape[1:]:
        raise ValueError("expected aligned (seed, condition, base case) arrays")
    if min(a.shape) < 1 or min(b.shape) < 1 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("empty or non-finite input")
    nseed = max(a.shape[0], b.shape[0])
    if a.shape[0] not in (1, nseed) or b.shape[0] not in (1, nseed):
        raise ValueError("learned comparisons need the same matched seeds")
    diff = np.broadcast_to(a, (nseed, *a.shape[1:])) - np.broadcast_to(b, (nseed, *b.shape[1:]))
    rng = np.random.default_rng(seed)
    boot = np.empty(repeats)
    for i in range(repeats):
        si = rng.integers(0, nseed, nseed)
        ci = rng.integers(0, diff.shape[2], diff.shape[2])
        boot[i] = diff[si][:, :, ci].mean()
    tail = (1 - confidence) / 2
    lo, hi = np.quantile(boot, [tail, 1 - tail])
    return {"difference_pp": float(diff.mean() * 100), "ci_low_pp": float(lo * 100),
            "ci_high_pp": float(hi * 100), "confidence": confidence, "bootstrap_repeats": repeats,
            "bootstrap_seed": seed, "training_seed_pairs": nseed, "base_case_clusters": diff.shape[2],
            "condition_count": diff.shape[1], "per_seed_difference_pp": (diff.mean(axis=(1, 2)) * 100).tolist()}
