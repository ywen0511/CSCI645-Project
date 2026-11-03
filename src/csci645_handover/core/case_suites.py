"""Fixed case suites (development / validation / final) and the training perturbation sampler.

Each case is initialized from its own RNG stream: ``numpy.random.SeedSequence([suite_seed, condition_index,
case_index])``, so case content never depends on vector-environment scheduling. Case IDs carry the
suite prefix, so suites cannot share IDs. The suite hash is the SHA-256 of the canonical JSONL bytes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

SUITE_VERSION = 1


def _case_rng(seed: int, cond_idx: int, case_idx: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([int(seed), int(cond_idx), int(case_idx)]))


def make_condition_cases(suite: str, seed: int, cond_idx: int, cond: dict, n: int, config_id: str) -> list[dict]:
    """Cases for one condition: per-axis uniform position in [-b, b], fixed signed release offset."""
    cases = []
    b = float(cond["position_bound_m"])
    for i in range(n):
        rng = _case_rng(seed, cond_idx, i)
        offset = rng.uniform(-b, b, size=3) if b > 0 else np.zeros(3)
        cases.append({
            "case_id": f"{suite}-{cond['id']}-{i:04d}",
            "suite": suite,
            "condition": cond["id"],
            "distribution": cond.get("distribution", ""),
            "requested_offset_xyz_m": [round(float(v), 9) for v in offset],
            "release_offset_s": round(float(cond["release_offset_s"]), 9),
            "init_seed": int(rng.integers(0, 2**31 - 1)),
            "config_id": config_id,
            "suite_version": SUITE_VERSION,
        })
    return cases


def make_validation_cases(seed: int, n: int, pos_bound: float, rel_bound: float, config_id: str) -> list[dict]:
    """Validation cases sampled from the final training distribution (uniform position and timing)."""
    cases = []
    for i in range(n):
        rng = _case_rng(seed, 0, i)
        offset = rng.uniform(-pos_bound, pos_bound, size=3)
        rel = rng.uniform(-rel_bound, rel_bound)
        cases.append({
            "case_id": f"validation-train_dist-{i:04d}",
            "suite": "validation",
            "condition": "train_dist",
            "distribution": "final_training_distribution",
            "requested_offset_xyz_m": [round(float(v), 9) for v in offset],
            "release_offset_s": round(float(rel), 9),
            "init_seed": int(rng.integers(0, 2**31 - 1)),
            "config_id": config_id,
            "suite_version": SUITE_VERSION,
        })
    return cases


def build_suites(protocol: dict, config_id: str, dev_per_condition: int = 50) -> dict[str, list[dict]]:
    ev = protocol["evaluation"]
    tr = protocol["training"]
    final_stage = tr["curriculum"][-1]
    suites = {
        "final": [],
        "validation": make_validation_cases(
            ev["validation_suite_seed"], tr["validation_episodes"], final_stage["position_bound_m"],
            final_stage["release_offset_bound_s"], config_id,
        ),
        "development": [],
    }
    for ci, cond in enumerate(ev["conditions"]):
        suites["final"] += make_condition_cases("final", ev["suite_seed"], ci, cond, ev["episodes_per_condition"], config_id)
        suites["development"] += make_condition_cases(
            "development", ev["development_suite_seed"], ci, cond, dev_per_condition, config_id
        )
    return suites


def canonical_jsonl(cases: list[dict]) -> bytes:
    return "".join(json.dumps(c, sort_keys=True, separators=(",", ":")) + "\n" for c in cases).encode()


def suite_hash(cases: list[dict]) -> str:
    return hashlib.sha256(canonical_jsonl(cases)).hexdigest()


def write_suite(path: str | Path, cases: list[dict]) -> str:
    data = canonical_jsonl(cases)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def read_suite(path: str | Path) -> tuple[list[dict], str]:
    data = Path(path).read_bytes()
    cases = [json.loads(line) for line in data.decode().splitlines() if line.strip()]
    ids = [c["case_id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate case IDs in {path}")
    return cases, hashlib.sha256(data).hexdigest()


def curriculum_stage(curriculum: list[dict], fraction: float) -> dict:
    """Transition-fraction curriculum stage (fixed schedule, identical for all methods)."""
    for stage in curriculum:
        if stage["fraction_start"] - 1e-12 <= fraction < stage["fraction_end"]:
            return stage
    return curriculum[-1]
