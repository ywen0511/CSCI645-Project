#!/usr/bin/env python3
"""Build the frozen v2 final-evaluation matrices and the expected-count manifest (CPU only).

    python3 scripts/make_v2_final_matrices.py --protocol configs/v2/protocol.json \
        --train-root <runs>/v2/final/train --selection results/v2/final/selection/selection.json \
        --output configs/v2/matrices/final

Deterministic controllers from ``protocol.deterministic_controllers`` are deduplicated by their normalized
runtime configuration (method flags + alignment bound + component flags + constant offset); a duplicate is
not re-run and is listed in ``reuse`` of ``final_manifest.json``. Learned entries per run: step 0, the
selected checkpoint and the final checkpoint (absolute paths). Expected episodes = entries x cases.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

METHOD_FLAGS = {"nominal": (False, False, False), "geometry": (True, False, False), "residual": (False, True, True),
                "combined": (True, True, True), "combined_no_phase": (True, True, False)}


def normalized(method: str, ov: dict, base: dict) -> str:
    geo, res, phase = METHOD_FLAGS[method]
    full = {"geometry_enabled": geo, "residual_enabled": res, "phase_input": phase,
            "align_max": ov.get("align_max", base.get("align_max", 0.010)),
            "geom_align": ov.get("geom_align", True), "geom_anchor": ov.get("geom_anchor", True),
            "geom_gate": ov.get("geom_gate", True), "constant_residual_m": ov.get("constant_residual_m")}
    if not geo:  # geometry parameters are unused without geometry
        for k in ("align_max", "geom_align", "geom_anchor", "geom_gate"):
            full[k] = None
    return json.dumps(full, sort_keys=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--protocol", default="configs/v2/protocol.json")
    ap.add_argument("--train-root", default=None)
    ap.add_argument("--selection", default=None)
    ap.add_argument("--det-only", action="store_true", help="Only the deterministic matrices (written at freeze time).")
    ap.add_argument("--relative", action="store_true",
                    help="Write checkpoint paths relative to the training root (pass it to eval_matrix.py --checkpoint-root).")
    ap.add_argument("--suite", default="configs/v2/suites/final.jsonl")
    ap.add_argument("--matrix-protocol", default="configs/v2/frozen/protocol.json",
                    help="Protocol file referenced by the matrices (env/PPO overrides at evaluation time).")
    ap.add_argument("--output", default="configs/v2/matrices/final")
    a = ap.parse_args()
    P = json.loads((ROOT / a.protocol).read_text())
    base = P["env_overrides"]
    n_cases = sum(1 for x in (ROOT / a.suite).read_text().splitlines() if x.strip())
    out = ROOT / a.output
    out.mkdir(parents=True, exist_ok=True)
    common = {"suite": a.suite, "num_envs": P["evaluation"]["num_envs"], "protocol": a.matrix_protocol, "trace_cases": []}
    seen, det_entries, reuse = {}, [], {}
    order = sorted(P["deterministic_controllers"], key=lambda k: (k.startswith(("ablation", "bound")), k))
    for cid in order:  # named controllers own their records; ablation/bound duplicates reuse them
        c = P["deterministic_controllers"][cid]
        key = normalized(c["method"], c["overrides"], base)
        if key in seen:
            reuse[cid] = seen[key]
            continue
        seen[key] = cid
        det_entries.append({"id": cid, "group": c.get("role", ""), "method": c["method"], "overrides": c["overrides"]})
    # split deterministic entries into 3 balanced jobs
    mats = {}
    for i in range(3):
        mats[f"final_det_{i}"] = {"name": f"final_det_{i}", **common, "entries": det_entries[i::3]}
    learned_runs = []
    if a.det_only:
        methods = []
    else:
        sel = json.loads(Path(a.selection).read_text())
        methods = P["training"]["methods"]
    for m in methods:
        for s in P["training"]["seeds"]:
            rid = f"{m}_seed{s}"
            rd = Path(a.train_root) / rid
            tags = {"untrained": "step_000000000", "selected": sel[rid]["selected"], "final": "final"}
            entries = [{"id": f"{rid}__{role}", "group": role, "method": m, "training_seed": s, "run_id": rid,
                        "checkpoint": (f"{rid}/checkpoints/{tag}.pt" if a.relative else str(rd / "checkpoints" / f"{tag}.pt")),
                        "role": role, "checkpoint_tag": tag}
                       for role, tag in tags.items()]
            mats[f"final_{rid}"] = {"name": f"final_{rid}", **common, "entries": entries}
            learned_runs.append(rid)
    expected = {}
    for name, mx in mats.items():
        (out / f"{name}.json").write_text(json.dumps(mx, indent=1) + "\n")
        for e in mx["entries"]:
            expected[e["id"]] = n_cases
    manifest = {"suite": a.suite, "cases": n_cases, "matrices": sorted(mats), "expected_episodes": expected,
                "expected_total": sum(expected.values()), "reuse": reuse,
                "reuse_rule": "identical normalized controller configuration (method flags, alignment bound, component flags, constant)",
                "learned_runs": learned_runs}
    if a.det_only:
        manifest["note"] = "deterministic part only (written at freeze); learned entries are added after selection"
        (out / "final_manifest_det.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
        print(f"det-only: {len(expected)} entries, {manifest['expected_total']} episodes; reuse: {reuse}")
        return
    (out / "final_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"{len(mats)} matrices, {len(expected)} entries, {manifest['expected_total']} episodes; reuse: {reuse}")


if __name__ == "__main__":
    main()
