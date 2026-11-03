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
