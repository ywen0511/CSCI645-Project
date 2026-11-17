"""CPU-only v3 case design and integrity checks (standard library only)."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


CONDITIONS = {
    "clean": (0.0, 0.0, 0),
    "physical_only": (0.0, 0.0, 0),
    "bias_2mm": (0.002, 0.0, 0),
    "bias_5mm": (0.005, 0.0, 0),
    "bias_10mm": (0.010, 0.0, 0),
    "noise_1mm": (0.0, 0.001, 0),
    "noise_2mm": (0.0, 0.002, 0),
    "noise_4mm": (0.0, 0.004, 0),
    "delay_1step": (0.0, 0.0, 1),
    "delay_2step": (0.0, 0.0, 2),
    "delay_4step": (0.0, 0.0, 4),
    "mixed_id": (0.005, 0.002, 2),
    "mixed_ood": (0.010, 0.004, 4),
}
VALIDATION = ("clean", "physical_only", "bias_5mm", "noise_2mm", "delay_2step", "mixed_id")
SPLIT_SEEDS = {"development": 6455101, "validation": 6455201, "final": 6455301}
SPLIT_COUNTS = {"development": 24, "validation": 40, "final": 200}


def case_seed(*parts) -> int:
    key = ":".join(str(p) for p in parts)
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], "big") & 0x7FFFFFFF


def make_cases(split: str) -> list[dict]:
    """Physical draws are shared across severities; clusters carry base_case_id.

    Bias is random-sign per axis at the stated amplitude, not uniformly smaller.
    In mixed_id/mixed_ood, bias is uniform within its bound. Noise sigma and delay
    are fixed per condition; the training mix draws their magnitudes uniformly.
    """
    seed, count = SPLIT_SEEDS[split], SPLIT_COUNTS[split]
    conditions = VALIDATION if split == "validation" else CONDITIONS
    rows = []
    for condition in conditions:
        bound, sigma, delay = CONDITIONS[condition]
        for i in range(count):
            rng = random.Random(case_seed(seed, i, "physical"))
            offset = [round(rng.uniform(-0.02, 0.02), 9) for _ in range(3)]
            release = round(rng.uniform(-0.30, 0.30), 9)
            brng = random.Random(case_seed(seed, i, "bias"))
            bias = [round(brng.uniform(-bound, bound), 9) if condition.startswith("mixed")
                    else bound * brng.choice([-1, 1]) for _ in range(3)]
            if condition == "clean":
                offset, release = [0.0, 0.0, 0.0], 0.0
            rows.append({
                "case_id": f"v3-{split}-{condition}-{i:04d}",
                "base_case_id": f"v3-{split}-{i:04d}",
                "suite": f"v3-{split}", "suite_version": 3, "config_id": "v3",
                "condition": condition, "requested_offset_xyz_m": offset,
                "release_offset_s": release, "init_seed": case_seed(seed, i, "init"),
                "observation_error": {"seed": case_seed(seed, i, "sensor"), "bias_xyz_m": bias,
                                      "noise_std_m": sigma, "delay_steps": delay},
            })
    return rows


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def validate_records(rows: list[dict], cases: list[dict], expected: dict, *, complete=False) -> dict:
    """Fail closed on stale cache, extra/duplicate IDs, or changed corruption metadata."""
    by_id = {c["case_id"]: c for c in cases}
    if len(by_id) != len(cases):
        raise ValueError("duplicate scheduled case ID")
    seen = set()
    for row in rows:
        cid = row["case_id"]
        if cid not in by_id or cid in seen:
            raise ValueError(f"unexpected or duplicate case {cid}")
        seen.add(cid)
        if row.get("condition") != by_id[cid]["condition"]:
            raise ValueError(f"{cid}: mismatched condition")
        for key, value in expected.items():
            if row.get(key) != value:
                raise ValueError(f"{cid}: stale {key}")
        if row.get("observation_error") != by_id[cid].get("observation_error"):
            raise ValueError(f"{cid}: mismatched observation_error")
        if not isinstance(row.get("success"), bool) or not isinstance(row.get("reset_valid"), bool):
            raise ValueError(f"{cid}: malformed outcome flags")
        if row["success"] and (not row["reset_valid"] or row.get("terminal_reason") != "success"):
            raise ValueError(f"{cid}: inconsistent success")
    missing = sorted(set(by_id) - seen)
    if complete and missing:
        raise ValueError(f"missing {len(missing)} scheduled cases")
    return {"scheduled": len(cases), "recorded": len(rows), "missing": len(missing),
            "invalid_resets": sum(not r["reset_valid"] for r in rows),
            "infra_errors": sum(r.get("terminal_reason") == "infra_error" for r in rows)}
