#!/usr/bin/env python3
"""Write results/v3/run_index.json: every v3 training run (formal, pilot, smoke/resume) with status, lineage,
selection and the raw-record files that evaluate it (CPU, standard library).

    python3 scripts/v3_run_index.py --runs <runs root holding candidate/ and formal/>

Paths are relative to the runs root, which is the layout of the extracted release (formal/train/<run>/...).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--output", default=str(ROOT / "results/v3/run_index.json"))
    a = ap.parse_args()
    R = Path(a.runs)
    sel = json.loads((ROOT / "results/v3/selection/selection.json").read_text())
    idx = json.loads((ROOT / "configs/v3/final_matrix_index.json").read_text())
    runs = []
    for d in sorted((R / "formal/train").iterdir()):
        if not d.is_dir():
            continue
        meta = json.loads((d / "run.json").read_text())
        done = json.loads((d / "DONE.json").read_text())
        val = sorted(p.relative_to(R / "formal").as_posix() for p in (R / "formal/validation" / d.name).rglob(f"{d.name}__*.jsonl"))
        fin = {e["role"]: e["records"] for e in idx["entries"] if e["seed"] is not None and f"{e['family']}_s{e['seed']}" == d.name}
        runs.append({"run": d.name, "type": "formal", "family": d.name.rsplit("_s", 1)[0], "seed": meta["seed"],
                     "status": "completed", "source_commit": meta["git"]["commit"], "source_dirty": meta["git"]["dirty"],
                     "protocol_sha256": meta["protocol_sha256"], "config_hash": meta["config_hash"],
                     "realized_transitions": done["transitions"], "iterations": done.get("iterations"),
                     "checkpoints": sorted(p.name for p in (d / "checkpoints").glob("*.pt")),
                     "selected": sel[d.name]["selected"], "selected_validation_success": sel[d.name]["success_rate"],
                     "validation_records": val, "final_records": fin, "selection_rationale": f"results/v3/selection/{d.name}.json"})
    for sub, typ in (("pilot", "pilot"), ("smoke", "smoke")):
        base = R / "candidate" / sub
        for d in sorted(base.iterdir()) if base.exists() else []:
            if d.is_dir() and (d / "run.json").exists():
                meta = json.loads((d / "run.json").read_text())
                runs.append({"run": d.name, "type": typ + ("_resume" if d.name.endswith("_resume") else ""), "seed": meta["seed"],
                             "status": "completed" if (d / "DONE.json").exists() else "incomplete",
                             "source_commit": meta["git"]["commit"], "source_dirty": meta["git"]["dirty"],
                             "checkpoints": sorted(p.name for p in (d / "checkpoints").glob("*.pt"))})
    sup = R / "superseded"
    out = {"runs": runs, "formal": sum(r["type"] == "formal" for r in runs),
           "superseded_attempts": sorted(p.relative_to(R).as_posix() for p in sup.glob("*/*/*") if p.is_dir()) if sup.exists() else [],
           "note": "superseded/: the first acceptance/development attempt at an earlier candidate commit (Kit shutdown hang); "
                   "kept and published, not used for any result (docs/v3/DECISIONS.md)"}
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(runs)} runs ({out['formal']} formal), {len(out['superseded_attempts'])} superseded entries")


if __name__ == "__main__":
    main()
