#!/usr/bin/env python3
"""Build results/run_index.json for analyze.py from a results directory (all paths relative to the index).

Expected layout under --runs (same for the live run folder and the downloaded results archive):
    eval/<run_id>.jsonl or eval/<run_id>__<ckpt>.jsonl      final-evaluation records
    validation/<run_id>__<ckpt>.jsonl                         validation records per candidate
    train/<run_id>/train_log.jsonl (+ checkpoints.jsonl, run.json)
    protocol.json or configs/frozen/protocol.json; suites/final.jsonl or configs/frozen/suites/final.jsonl

Usage:
    python3 scripts/build_run_index.py --runs results --output results/run_index.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def first(root: Path, *cands: str) -> Path:
    for c in cands:
        if (root / c).exists():
            return root / c
    raise SystemExit(f"none of {cands} under {root}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--protocol", default=None)
    ap.add_argument("--suites", default=None)
    a = ap.parse_args()
    root = Path(a.runs).resolve()
    out = Path(a.output).resolve()
    base = out.parent
    rel = lambda p: os.path.relpath(Path(p).resolve(), base)  # noqa: E731
    repo = Path(__file__).resolve().parents[1]
    proto = Path(a.protocol) if a.protocol else (root / "protocol.json" if (root / "protocol.json").exists()
                                                 else repo / "configs/frozen/protocol.json")
    suites = Path(a.suites) if a.suites else (root / "suites" if (root / "suites").exists()
                                              else repo / "configs/frozen/suites")
    protocol = json.loads(proto.read_text())
    learned = {m["id"] for m in protocol["methods"] if m["learned"]}
    idx = {"protocol": rel(proto), "suites": {"final": rel(suites / "final.jsonl"),
                                              "validation": rel(suites / "validation.jsonl")},
           "final_eval": [], "validation": [], "training": []}
    for f in sorted((root / "eval").glob("*.jsonl")):
        if f.name.startswith("eval_runs"):
            continue
        rid = f.stem.split("__")[0]
        method = rid.split("_seed")[0] if "_seed" in rid else rid
        seed = int(rid.split("_seed")[1]) if "_seed" in rid else None
        idx["final_eval"].append({"run_id": rid, "method": method, "training_seed": seed, "file": rel(f)})
    vals: dict[str, list[str]] = {}
    for f in sorted((root / "validation").glob("*__*.jsonl")):
        vals.setdefault(f.stem.split("__")[0], []).append(rel(f))
    for rid, files in sorted(vals.items()):
        idx["validation"].append({"run_id": rid, "method": rid.split("_seed")[0], "training_seed": int(rid.split("_seed")[1]),
                                  "files": files})
    for d in sorted((root / "train").glob("*_seed*")):
        if (d / "train_log.jsonl").exists():
            m = d.name.split("_seed")[0]
            if m in learned:
                idx["training"].append({"run_id": d.name, "method": m, "training_seed": int(d.name.split("_seed")[1]),
                                        "train_log": rel(d / "train_log.jsonl")})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(idx, indent=2))
    print(f"index: {len(idx['final_eval'])} final-eval files, {len(idx['validation'])} validation runs, "
          f"{len(idx['training'])} training logs -> {out}")


if __name__ == "__main__":
    main()
