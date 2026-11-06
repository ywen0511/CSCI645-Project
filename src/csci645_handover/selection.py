"""Validation-candidate choice and checkpoint selection (identical rule for all nine runs)."""

from __future__ import annotations

import json
from pathlib import Path

VALIDATION_BOUNDARIES = (0, 2_000_000, 4_000_000, 6_000_000, 8_000_000, 10_000_000)


def validation_candidates(checkpoint_ledger: str | Path) -> list[dict]:
    """First periodic checkpoint at or after each 2M-transition boundary (plus step 0)."""
    rows = [json.loads(x) for x in Path(checkpoint_ledger).read_text().splitlines() if x.strip()]
    steps = {}
    for r in rows:
        if r["tag"].startswith("step_"):
            steps[r["transitions"]] = r
    picked: list[dict] = []
    for b in VALIDATION_BOUNDARIES:
        ok = sorted(t for t in steps if t >= b)
        if ok and steps[ok[0]] not in picked:
            picked.append(steps[ok[0]])
    return picked


def select(candidates: list[dict]) -> dict:
    """Highest validation success rate; ties: lowest drop rate, then earliest transitions.

    Each candidate needs ``success_rate``, ``drop_rate`` and ``transitions``.
    """
    if not candidates:
        raise ValueError("no candidates")
    return sorted(candidates, key=lambda r: (-(r["success_rate"] or 0.0), r["drop_rate"] or 0.0, r["transitions"]))[0]


def score_validation_file(path: str | Path) -> dict:
    rows = [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    valid = [r for r in rows if r["reset_valid"] and r["terminal_reason"] != "infrastructure_error"]
    n = len(valid)
    return {
        "file": Path(path).name, "checkpoint": rows[0].get("checkpoint") if rows else None,
        "checkpoint_sha256": rows[0].get("checkpoint_sha256") if rows else None,
        "transitions": rows[0].get("checkpoint_transitions") if rows else None,
        "scheduled": len(rows), "valid": n,
        "success_rate": sum(r["success"] for r in valid) / n if n else None,
        "drop_rate": sum(r["drop"] for r in valid) / n if n else None,
    }


# ---------------------------------------------------------------------------------------------- v2 rule
V2_CANDIDATE_BOUNDARIES = (2_000_000, 4_000_000, 6_000_000, 8_000_000, 10_000_000)


def validation_candidates_v2(checkpoint_ledger: str | Path) -> list[dict]:
    """First periodic checkpoint at or after each of 2M..10M transitions. Step 0 is never a candidate."""
    rows = [json.loads(x) for x in Path(checkpoint_ledger).read_text().splitlines() if x.strip()]
    steps = {}
    for r in rows:
        if r["tag"].startswith("step_") and r["transitions"] > 0:
            steps[r["transitions"]] = r
    picked: list[dict] = []
    for b in V2_CANDIDATE_BOUNDARIES:
        ok = sorted(t for t in steps if t >= b)
        if ok and steps[ok[0]] not in picked:
            picked.append(steps[ok[0]])
    return picked


def select_v2(candidates: list[dict]) -> dict:
    """v2 rule: highest validation success; then lowest collision-episode rate; then lowest mean bounded
    residual squared norm over scored steps; then the latest transition count. Step 0 is rejected."""
    cands = [c for c in candidates if c["transitions"] and c["transitions"] > 0]
    if not cands:
        raise ValueError("no trained candidates")
    for c in cands:
        for k in ("success_rate", "collision_rate", "residual_sq_norm_mean_m2"):
            if c.get(k) is None:
                raise ValueError(f"candidate {c.get('checkpoint')} lacks {k}")
    return sorted(cands, key=lambda r: (-r["success_rate"], r["collision_rate"], r["residual_sq_norm_mean_m2"],
                                        -r["transitions"]))[0]


def score_validation_records_v2(rows: list[dict]) -> dict:
    """Validation metrics for the v2 rule from one checkpoint's records (valid resets only)."""
    valid = [r for r in rows if r["reset_valid"] and r["terminal_reason"] != "infrastructure_error"]
    n = len(valid)
    steps = sum(r["scored_steps"] for r in valid)
    sq = sum(r["residual_sq_norm_mean_m2"] * r["scored_steps"] for r in valid)
    return {
        "checkpoint": rows[0].get("checkpoint") if rows else None,
        "checkpoint_sha256": rows[0].get("checkpoint_sha256") if rows else None,
        "transitions": rows[0].get("checkpoint_transitions") if rows else None,
        "scheduled": len(rows), "valid": n,
        "success_rate": sum(r["success"] for r in valid) / n if n else None,
        "collision_rate": sum(r["collision"] for r in valid) / n if n else None,
        "drop_rate": sum(r["drop"] for r in valid) / n if n else None,
        "residual_sq_norm_mean_m2": sq / steps if steps else None,
    }
