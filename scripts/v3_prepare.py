#!/usr/bin/env python3
"""Generate v3 CPU inputs; never imports Isaac Lab or starts simulation.

Development generates runnable candidate matrices and training protocols. Final
generation requires a committed freeze manifest; see V3_EXECUTION.md.
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover.v3_protocol import make_cases, sha256, write_json


def prepare(root: Path, final=False):
    v3 = root / "configs/v3"
    spec = json.loads((v3 / "protocol.draft.json").read_text())
    base = json.loads((root / "configs/v2/protocol.json").read_text())
    manifest = {}
    splits = ["development", "validation"]
    if final:
        freeze = json.loads((v3 / "FREEZE.json").read_text())
        if freeze.get("status") != "frozen" or not freeze.get("source_commit"):
            raise ValueError("final requires a frozen source commit")
        if not freeze.get("files") or not freeze.get("gpu_acceptance_evidence"):
            raise ValueError("freeze must include hashed inputs and GPU acceptance evidence")
        subprocess.run(["git", "-C", str(root), "cat-file", "-e", freeze["source_commit"] + "^{commit}"], check=True)
        for rel, digest in freeze["files"].items():
            if sha256(root / rel) != digest:
                raise ValueError(f"freeze input changed: {rel}")
        splits = ["final"]
    for split in splits:
        p = v3 / "suites" / f"{split}.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        rows = make_cases(split)
        content = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        if p.exists() and p.read_text() != content:
            raise ValueError(f"refusing to replace a different suite: {p}")
        p.write_text(content)
        manifest[split] = {"path": str(p.relative_to(root)), "cases": len(rows), "sha256": sha256(p)}
    path = v3 / "SUITES.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    write_json(path, {**old, **manifest})
    if final:
        return manifest
    for name, profile in spec["profiles"].items():
        protocol = {"protocol_id": "v3-draft-" + name, "status": "pilot_only; remote GPU acceptance pending",
                    "training": copy.deepcopy(base["training"]), "env_overrides": copy.deepcopy(base["env_overrides"]),
                    "ppo_overrides": copy.deepcopy(base["ppo_overrides"])}
        protocol["training"].update(seeds=profile.get("seeds", spec["training_seeds"]), methods=[profile["method"]])
        protocol["training"]["final_transitions_per_run"] = spec["formal_transition_budget_per_run"]
        protocol["env_overrides"].update(observation_history=profile["history"],
                                         observation_history_mode=profile.get("history_mode", "stack"),
                                         observation_sensor={**spec["sensor"], **profile.get("sensor_overrides", {})})
        write_json(v3 / "training" / f"{name}.json", protocol)
    # Separate process per estimator: EMA/reference are not runtime-switchable fields.
    for alpha in spec["baseline_search"]["ema_alphas"]:
        for giver in (False, True):
            key = f"ema{str(alpha).replace('.', 'p')}_giver{int(giver)}"
            entries = [{"id": "nominal", "method": "nominal", "trace": True}]
            for bound in spec["baseline_search"]["alignment_bounds_m"]:
                for offset in spec["baseline_search"]["constant_x_m"]:
                    entries.append({"id": f"geom{round(bound*1000):02d}_x{round(offset*1000):+03d}",
                                    "method": "geometry", "overrides": {"align_max": bound,
                                    "constant_residual_m": [offset, 0, 0]}, "trace": offset == 0})
            write_json(v3 / "matrices/development" / f"{key}.json", {
                "name": "v3_development_" + key, "protocol": "configs/v2/protocol.json",
                "suite": "configs/v3/suites/development.jsonl", "num_envs": 312,
                "base_overrides": {"observation_sensor": {**spec["sensor"], "ema_alpha": alpha},
                                   "observation_giver_reference": giver},
                "trace_cases": ["v3-development-mixed_id-0000", "v3-development-noise_2mm-0000"],
                "entries": entries,
            })
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(ROOT, args.final), indent=2))
