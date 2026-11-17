#!/usr/bin/env python3
"""Build configs/v3/final_matrix_index.json (+ case/suite manifest and declared job counts) from final records.

    python3 scripts/v3_build_index.py --runs <runs root containing final/> [--output configs/v3/final_matrix_index.json]

Record paths are relative to the runs root (the analysis is run with --root <runs root>, locally or on the
extracted release). Expected provenance (entry, suite/config/controller/checkpoint hashes, source commit, clean
flag) is taken from the records and must be identical in every row (checked again by v3_analyze.py). Aliased
baseline roles (identical configuration) point to the same file and carry alias_of.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = ("entry_id", "suite_hash", "config_hash", "controller_hash", "checkpoint_sha256", "source_commit", "source_dirty")
FAMILIES = {"combined_clean_ff": 5, "combined_robust_ff": 5, "combined_robust_history": 5, "residual_robust_history": 5,
            "combined_robust_repeat": 3}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def expected(path: Path) -> dict:
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    e = {k: rows[0].get(k) for k in KEYS}
    for r in rows:
        if any(r.get(k) != e[k] for k in KEYS):
            raise SystemExit(f"{path}: provenance differs between rows")
    return e


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--output", default=str(ROOT / "configs/v3/final_matrix_index.json"))
    a = ap.parse_args()
    R = Path(a.runs)
    sel = json.loads((ROOT / "results/v3/selection/selection.json").read_text())
    aliases = json.loads((ROOT / "configs/v3/final_matrices/baseline_aliases.json").read_text())
    entries = []
    for role in ("nominal", "geometry_common", "geometry_best_constant", "geometry_raw", "geometry_filtered", "geometry_giver"):
        src = aliases.get(role, role)
        p = R / "final" / src / f"{src}.jsonl"
        entries.append({"family": role, "seed": None, "role": "baseline", "records": str(p.relative_to(R)), "sha256": sha(p),
                        "expected": expected(p), **({"alias_of": src} if role in aliases else {})})
    for run, s in sorted(sel.items()):
        fam, seed = run.rsplit("_s", 1)
        for role in ("selected", "final"):
            p = R / "final" / run / role / f"{run}__{role}.jsonl"
            entries.append({"family": fam, "seed": int(seed), "role": role, "records": str(p.relative_to(R)), "sha256": sha(p),
                            "checkpoint_tag": s["selected"] if role == "selected" else "final", "expected": expected(p)})
    suite = ROOT / "configs/v3/suites/final.jsonl"
    cases = [json.loads(l) for l in suite.read_text().splitlines() if l.strip()]
    found = {}
    for e in entries:
        if e["seed"] is not None:
            found.setdefault(e["family"], set()).add(e["seed"])
    missing = {f: n - len(found.get(f, ())) for f, n in FAMILIES.items() if len(found.get(f, ())) != n}
    if missing:
        raise SystemExit(f"missing formal runs in the final matrix: {missing}")
    index = {"suite": "configs/v3/suites/final.jsonl", "suite_sha256": sha(suite), "records_root": "<runs root>",
             "entries": entries,
             "case_manifest": {"cases": len(cases), "conditions": sorted({c["condition"] for c in cases}),
                               "base_case_clusters": len({c["base_case_id"] for c in cases}),
                               "clean_condition_note": "the clean condition repeats one physical setup (reliability check)"},
             "declared_counts": {"logical_entries": len(entries), "logical_episodes": len(entries) * len(cases),
                                 "executed_entries": len(entries) - len(aliases),
                                 "executed_episodes": (len(entries) - len(aliases)) * len(cases),
                                 "baseline_aliases": aliases, "learned_runs": sum(FAMILIES.values()),
                                 "processes": "one fresh simulator process per executed entry, batch 256"}}
    Path(a.output).write_text(json.dumps(index, indent=1) + "\n")
    print(json.dumps(index["declared_counts"], indent=1))


if __name__ == "__main__":
    main()
