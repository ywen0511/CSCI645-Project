#!/usr/bin/env python3
"""Write an eval_matrix.py matrix for checkpoints of one or more training runs.

    python3 scripts/make_ckpt_matrix.py --run-dir runs/v2/final/train/combined_seed11 --method combined --seed 11 \
        --suite configs/v2/suites/validation.jsonl --protocol configs/v2/protocol.json \
        --tags v2_candidates --name val_combined_seed11 --output matrix.json

--tags: ``all`` (every periodic step + final), ``v2_candidates`` (first checkpoint at/after 2M..10M; never step 0),
``final``, ``step0``, or a comma list of tags. Several --run-dir/--method/--seed triples may be given.
Checkpoint paths are written as absolute paths.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from csci645_handover.selection import validation_candidates_v2  # noqa: E402


def tags_for(run_dir: Path, spec: str) -> list[str]:
    ledger = run_dir / "checkpoints.jsonl"
    rows = [json.loads(x) for x in ledger.read_text().splitlines() if x.strip()]
    if spec == "all":
        return [r["tag"] for r in rows if r["tag"].startswith("step_")] + ["final"]
    if spec == "v2_candidates":
        return [r["tag"] for r in validation_candidates_v2(ledger)]
    if spec == "final":
        return ["final"]
    if spec == "step0":
        return ["step_000000000"]
    return [t for t in spec.split(",") if t]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", action="append", required=True)
    ap.add_argument("--method", action="append", required=True)
    ap.add_argument("--seed", action="append", type=int, required=True)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--tags", default="all")
    ap.add_argument("--name", required=True)
    ap.add_argument("--num-envs", type=int, default=None)
    ap.add_argument("--prefix", default="", help="Entry-ID prefix (e.g. 'sel_' or 'final_').")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    if not (len(a.run_dir) == len(a.method) == len(a.seed)):
        raise SystemExit("--run-dir, --method and --seed must be given the same number of times")
    entries = []
    for rd, m, s in zip(a.run_dir, a.method, a.seed):
        rd = Path(rd).resolve()
        for tag in tags_for(rd, a.tags):
            ck = rd / "checkpoints" / f"{tag}.pt"
            if not ck.exists():
                raise SystemExit(f"missing {ck}")
            entries.append({"id": f"{a.prefix}{rd.name}__{tag}", "group": rd.name, "method": m, "training_seed": s,
                            "run_id": rd.name, "checkpoint": str(ck)})
    n_cases = sum(1 for x in Path(a.suite).read_text().splitlines() if x.strip())
    mx = {"name": a.name, "suite": a.suite, "num_envs": a.num_envs or min(n_cases, 900), "protocol": a.protocol,
          "trace_cases": [], "entries": entries}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(mx, indent=1) + "\n")
    print(f"{a.output}: {len(entries)} entries")


if __name__ == "__main__":
    main()
