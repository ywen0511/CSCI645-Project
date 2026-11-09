"""CPU-only V4 case design and record integrity checks (standard library only).

A V4 case = base case (shared physical draw: joint start displacement + release-time offset) x condition
(in-grasp offset rule + translation-sensor corruption). Base cases are paired across conditions and methods;
grasp offsets and sensor seeds are drawn from separate keyed streams so that changing one never shifts another.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

SPLIT_SEEDS = {"development": 6456101, "validation": 6456201, "final": 6456301}
ANALYSIS_SEED = 6456401
TRAINING_SEEDS = (111, 222, 333, 444, 555)
SPLIT_COUNTS = {"development": 24, "validation": 40, "final": 200}
SUITE_VERSION = 4
AXES = "xyz"


def case_seed(*parts) -> int:
    key = ":".join(str(p) for p in parts)
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], "big") & 0x7FFFFFFF


def grasp_offset(rule: dict, rng: random.Random) -> list[float]:
    """In-grasp offset from a condition rule.

    rule = {"mode": "zero"} | {"mode": "sign", "magnitude_m": a, "axes": "xz"} (each listed axis +-a, random sign)
         | {"mode": "uniform", "bound_m": b, "axes": "xz"} (each listed axis uniform in [-b, b])
         | {"mode": "fixed", "xyz_m": [x, y, z]} (deterministic direction check)
         | {"mode": "sign_axis", "magnitude_m": a, "axis": "x", "sign": +1|-1|0} (one axis; sign 0 = random)
    """
    mode = rule.get("mode", "zero")
    out = [0.0, 0.0, 0.0]
    if mode == "zero":
        return out
    if mode == "fixed":
        return [round(float(v), 9) for v in rule["xyz_m"]]
    if mode == "sign_axis":
        s = rule.get("sign", 0) or rng.choice([-1, 1])
        out[AXES.index(rule["axis"])] = round(s * rule["magnitude_m"], 9)
        return out
    for ax in rule["axes"]:
        k = AXES.index(ax)
        if mode == "sign":
            out[k] = round(rule["magnitude_m"] * rng.choice([-1, 1]), 9)
        elif mode == "uniform":
            out[k] = round(rng.uniform(-rule["bound_m"], rule["bound_m"]), 9)
        else:
            raise ValueError(f"unknown grasp rule {mode}")
    return out


def sensor_error(rule: dict, rng: random.Random, seed: int) -> dict:
    """rule = {"bias_m": a, "bias_mode": "sign"|"uniform", "noise_std_m": s, "delay_steps": d}."""
    a = float(rule.get("bias_m", 0.0))
    if rule.get("bias_mode", "sign") == "uniform":
        bias = [round(rng.uniform(-a, a), 9) for _ in range(3)]
    else:
        bias = [round(a * rng.choice([-1, 1]), 9) for _ in range(3)]
    return {"seed": seed, "bias_xyz_m": bias, "noise_std_m": float(rule.get("noise_std_m", 0.0)),
            "delay_steps": int(rule.get("delay_steps", 0))}


def make_cases(split: str, conditions: dict, order: list[str], *, count: int | None = None,
               seed: int | None = None, prefix: str = "v4") -> list[dict]:
    """Deterministic paired cases. ``conditions[name] = {"grasp": rule, "sensor": rule, "physical": bool}``.

    physical False (clean) zeroes the joint displacement and release offset; True uses the base case's draw
    (joint start displacement uniform in +-2 cm per axis, release offset uniform in +-0.3 s, as in V3).
    """
    seed = SPLIT_SEEDS[split] if seed is None else seed
    count = SPLIT_COUNTS[split] if count is None else count
    rows = []
    for condition in order:
        spec = conditions[condition]
        for i in range(count):
            prng = random.Random(case_seed(seed, i, "physical"))
            offset = [round(prng.uniform(-0.02, 0.02), 9) for _ in range(3)]
            release = round(prng.uniform(-0.30, 0.30), 9)
            if not spec.get("physical", True):
                offset, release = [0.0, 0.0, 0.0], 0.0
            grng = random.Random(case_seed(seed, i, "grasp", condition))
            brng = random.Random(case_seed(seed, i, "bias"))
            rows.append({
                "case_id": f"{prefix}-{split}-{condition}-{i:04d}",
                "base_case_id": f"{prefix}-{split}-{i:04d}",
                "suite": f"{prefix}-{split}", "suite_version": SUITE_VERSION, "config_id": prefix,
                "condition": condition, "requested_offset_xyz_m": offset, "release_offset_s": release,
                "grasp_offset_xyz_m": grasp_offset(spec.get("grasp", {"mode": "zero"}), grng),
                "init_seed": case_seed(seed, i, "init"),
                "observation_error": sensor_error(spec.get("sensor", {}), brng, case_seed(seed, i, "sensor")),
            })
    return rows


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_jsonl(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def validate_records(rows: list[dict], cases: list[dict], expected: dict, *, complete=False) -> dict:
    """Fail closed on stale cache, extra/duplicate IDs, or changed corruption/grasp metadata."""
    by_id = {c["case_id"]: c for c in cases}
    if len(by_id) != len(cases):
        raise ValueError("duplicate scheduled case ID")
    seen = set()
    for row in rows:
        cid = row["case_id"]
        if cid not in by_id or cid in seen:
            raise ValueError(f"unexpected or duplicate case {cid}")
        seen.add(cid)
        case = by_id[cid]
        if row.get("condition") != case["condition"]:
            raise ValueError(f"{cid}: mismatched condition")
        for key, value in expected.items():
            if row.get(key) != value:
                raise ValueError(f"{cid}: stale {key}")
        if row.get("observation_error") != case.get("observation_error"):
            raise ValueError(f"{cid}: mismatched observation_error")
        if row.get("grasp_offset_requested_xyz_m") != [float(v) for v in case["grasp_offset_xyz_m"]]:
            raise ValueError(f"{cid}: mismatched grasp offset")
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


def probe_cases() -> list[dict]:
    """Development-only grasp feasibility probe (namespace: development seed, key "probe").

    Single-axis grids on x (bar axis) and z (vertical), a small y set (finger-closing axis, expected to be
    re-centred by the fingers), and xz diagonals; four base cases (one without joint displacement)."""
    grid = [-0.015, -0.010, -0.007, -0.005, -0.002, 0.002, 0.005, 0.007, 0.010, 0.015]
    points = {"g0": [0.0, 0.0, 0.0]}
    for ax, k in (("x", 0), ("z", 2)):
        for v in grid:
            p = [0.0, 0.0, 0.0]; p[k] = v
            points[f"{ax}{v * 1000:+.0f}"] = p
    for v in (-0.005, -0.002, 0.002, 0.005):
        points[f"y{v * 1000:+.0f}"] = [0.0, v, 0.0]
    for sx, sz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        for a in (0.005, 0.010):
            points[f"xz{sx * a * 1000:+.0f}{sz * a * 1000:+.0f}"] = [sx * a, 0.0, sz * a]
    conditions = {name: {"grasp": {"mode": "fixed", "xyz_m": p}, "sensor": {}, "physical": True}
                  for name, p in points.items()}
    rows = make_cases("development", conditions, list(points), count=4, seed=case_seed(SPLIT_SEEDS["development"], "probe"),
                      prefix="v4probe")
    for r in rows:  # base case 0 has no joint displacement or release offset
        if r["base_case_id"].endswith("-0000"):
            r["requested_offset_xyz_m"], r["release_offset_s"] = [0.0, 0.0, 0.0], 0.0
    return rows
