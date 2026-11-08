#!/usr/bin/env python3
"""Validate all declared v3 raw files and produce counts and paired effects on CPU.

Index schema: {"suite": "configs/v3/suites/final.jsonl", "entries": [
 {"family":"combined_robust_history", "seed":11, "role":"selected",
  "records":"runs/v3/final/...jsonl", "sha256":"...", "expected":{
  "entry_id":"...", "suite_hash":"...", "config_hash":"...", "controller_hash":"...",
  "checkpoint_sha256":"...", "source_commit":"...", "source_dirty":false}}]}.
Deterministic entries use seed=null, role="baseline". Learned selected/final entries
are separate even when they point to the same checkpoint bytes.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover.v3_analysis import paired_effect
from csci645_handover.v3_protocol import sha256, validate_records, write_json


def analyze(root, index_path, output, repeats=10000):
    index = json.loads(index_path.read_text())
    suite_path = root / index["suite"]
    cases = [json.loads(line) for line in suite_path.read_text().splitlines() if line.strip()]
    conditions = sorted({c["condition"] for c in cases})
    expected_keys = {"entry_id", "suite_hash", "config_hash", "controller_hash", "checkpoint_sha256", "source_commit", "source_dirty"}
    expected_families = {
        "combined_clean_ff": [11, 22, 33, 44, 55],
        "combined_robust_ff": [11, 22, 33, 44, 55],
        "combined_robust_history": [11, 22, 33, 44, 55],
        "residual_robust_history": [11, 22, 33, 44, 55],
        "combined_robust_repeat": [11, 22, 33],
    }
    required = {(family, role, seed) for family, seeds in expected_families.items()
                for role in ("selected", "final") for seed in seeds}
    required |= {(family, "baseline", None) for family in
                 ("nominal", "geometry_common", "geometry_best_constant", "geometry_raw", "geometry_filtered", "geometry_giver")}
    supplied = [(e["family"], e["role"], e["seed"]) for e in index["entries"]]
    if len(supplied) != len(set(supplied)) or set(supplied) != required:
        raise ValueError("main matrix must contain exactly 23 selected + 23 final + six baseline entries")
    groups, counts, reconciliation = {}, [], []
    for e in index["entries"]:
        if not expected_keys <= e["expected"].keys() or e["expected"]["source_dirty"] is not False:
            raise ValueError("incomplete provenance or dirty source in index")
        if e["expected"]["suite_hash"] != sha256(suite_path):
            raise ValueError("index suite hash mismatch")
        path = root / e["records"]
        if sha256(path) != e["sha256"]:
            raise ValueError(f"raw-file checksum mismatch: {path}")
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        check = validate_records(rows, cases, {**e["expected"], "training_seed": e["seed"]}, complete=True)
        reconciliation.append({"records": e["records"], **check})
        if check["invalid_resets"] or check["infra_errors"]:
            raise ValueError(f"unresolved invalid resets/infrastructure errors in {path}; reconcile before final analysis")
        key = (e["family"], e["role"], e["seed"])
        if key in groups:
            raise ValueError(f"duplicate controller/role/seed: {key}")
        groups[key] = {r["case_id"]: r for r in rows}
        for condition in conditions:
            selected = [r for r in rows if r["condition"] == condition]
            times = [r["completion_time_s"] for r in selected if r["success"]]
            counts.append({"family": e["family"], "role": e["role"], "seed": e["seed"], "condition": condition,
                           "scheduled": len(selected), "success": sum(r["success"] for r in selected),
                           "drop": sum(r["drop"] for r in selected), "collision": sum(r["collision"] for r in selected),
                           "success_rate": np.mean([r["success"] for r in selected]),
                           "completion_time_success_mean_s": np.mean(times) if times else None,
                           "unique_clean_initial_states": 1 if condition == "clean" else None})
    output.mkdir(parents=True, exist_ok=True)
    with (output / "per_seed_condition.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(counts[0]))
        writer.writeheader()
        writer.writerows(counts)
    comparisons = [
        ("combined_robust_history", "combined_robust_ff", True),
        ("combined_robust_history", "geometry_best_constant", True),
        ("combined_robust_ff", "combined_clean_ff", False),
        ("residual_robust_history", "nominal", False),
        ("combined_robust_history", "geometry_common", False),
        ("combined_robust_history", "combined_robust_repeat", False),
    ]
    def seeds_for(family, role):
        return sorted([s for f, r, s in groups if f == family and r == role], key=lambda s: -1 if s is None else s)

    def array(family, role, seeds, subset):
        order = [sorted([c for c in cases if c["condition"] == cond], key=lambda c: c["base_case_id"]) for cond in subset]
        clusters = [[c["base_case_id"] for c in cs] for cs in order]
        if any(cs != clusters[0] for cs in clusters):
            raise ValueError("unaligned base-case clusters")
        return np.array([[[groups[(family, role, s)][c["case_id"]]["success"] for c in cs] for cs in order] for s in seeds])

    effects = []
    for role in ("selected", "final"):
        for left, right, primary in comparisons:
            lr = role
            rr = "baseline" if seeds_for(right, "baseline") else role
            ls, rs = seeds_for(left, lr), seeds_for(right, rr)
            if not ls or not rs:
                raise ValueError(f"missing required comparison: {left}, {right}, {role}")
            if rs != [None]:
                shared = sorted(set(ls) & set(rs))
                if not shared:
                    raise ValueError("no paired training seeds")
                ls, rs = shared, shared
            for subset in (["mixed_id"], ["mixed_ood"], [c for c in conditions if c != "clean"]):
                a, b = array(left, lr, ls, subset), array(right, rr, rs, subset)
                result = paired_effect(a, b, repeats=repeats)
                effects.append({"left": left, "right": right, "role": role, "conditions": subset,
                                "primary": primary and role == "selected" and subset == ["mixed_id"],
                                "training_seeds_left": ls, "training_seeds_right": rs, **result})
                if effects[-1]["primary"]:
                    # Bonferroni intervals for the two predeclared primary effects.
                    effects[-1]["familywise_95_interval"] = paired_effect(a, b, repeats=repeats, confidence=0.975)
    write_json(output / "paired_effects.json", effects)
    write_json(output / "reconciliation.json", reconciliation)
    write_json(output / "analysis_manifest.json", {"index_sha256": sha256(index_path), "suite_sha256": sha256(suite_path),
                                                  "bootstrap": "paired training seed and shared base-case cluster; fixed conditions",
                                                  "outputs": {p.name: sha256(p) for p in sorted(output.iterdir()) if p.name != "analysis_manifest.json" and p.is_file()}})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", required=True)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--output", type=Path, default=ROOT / "results/v3/summary")
    ap.add_argument("--bootstrap-repeats", type=int, default=10000)
    a = ap.parse_args()
    analyze(a.root, Path(a.index), a.output, a.bootstrap_repeats)
