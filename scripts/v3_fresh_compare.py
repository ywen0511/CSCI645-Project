#!/usr/bin/env python3
"""Compare the fresh-download GPU verification outputs with the published final records (CPU).

    python3 scripts/v3_fresh_compare.py --x <extracted release with replay65/, reload/, resume_check/> \
        --output results/v3/verification/fresh_gpu.json

replay65: 65-case subset for geometry_common, geometry_best_constant and the five selected history policies
(batch 23, seed 6455501) vs the batch-256 final records: terminal reason and success agreement, plus identity of
each case's observation_error spec. reload: one selected checkpoint of every other formal profile on 13 cases
(first case of each condition). resume: two-iteration resume inspection (counters, optimizer, normalizer).
All mismatches are listed; nothing is excluded.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jl(p: Path):
    return {r["case_id"]: r for r in (json.loads(l) for l in p.read_text().splitlines() if l.strip())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--x", required=True)
    ap.add_argument("--output", default=str(ROOT / "results/v3/verification/fresh_gpu.json"))
    a = ap.parse_args()
    X = Path(a.x)
    idx = json.loads((ROOT / "configs/v3/final_matrix_index.json").read_text())
    rec = {(e["family"], e["role"], e["seed"]): e["records"] for e in idx["entries"]}
    out = {"replay65": [], "reload": [], "mismatches": []}

    def compare(kind, entry, path, final_path):
        new, old = jl(path), jl(X / final_path)
        row = {"entry": entry, "cases": len(new), "missing_in_final": sorted(set(new) - set(old)),
               "terminal_equal": sum(new[c]["terminal_reason"] == old[c]["terminal_reason"] for c in new if c in old),
               "success_equal": sum(new[c]["success"] == old[c]["success"] for c in new if c in old),
               "observation_error_equal": all(new[c]["observation_error"] == old[c]["observation_error"] for c in new if c in old),
               "checkpoint_sha256_equal": all(new[c].get("checkpoint_sha256") == old[c].get("checkpoint_sha256") for c in new if c in old),
               "success": sum(new[c]["success"] for c in new), "invalid_resets": sum(not new[c]["reset_valid"] for c in new)}
        for c in new:
            if c in old and new[c]["terminal_reason"] != old[c]["terminal_reason"]:
                out["mismatches"].append({"kind": kind, "entry": entry, "case": c, "fresh": new[c]["terminal_reason"],
                                          "published": old[c]["terminal_reason"]})
        out[kind].append(row)

    for d in sorted((X / "replay65").iterdir()):
        e = d.name
        if "__" in e:
            fam, s = e.split("__")[0].rsplit("_s", 1)
            key = (fam, "selected", int(s))
        else:
            key = (e, "baseline", None)
        compare("replay65", e, d / f"{e}.jsonl", rec[key])
    for d in sorted((X / "reload").iterdir()):
        f = next(d.glob("*__selected.jsonl"))
        fam, s = f.stem.split("__")[0].rsplit("_s", 1)
        compare("reload", f.stem, f, rec[(fam, "selected", int(s))])
    ins = X / "resume_check/inspect.json"
    out["resume"] = json.loads(ins.read_text()) if ins.exists() else None
    out["summary"] = {"replay65_episodes": sum(r["cases"] for r in out["replay65"]),
                      "replay65_terminal_equal": sum(r["terminal_equal"] for r in out["replay65"]),
                      "reload_episodes": sum(r["cases"] for r in out["reload"]),
                      "reload_terminal_equal": sum(r["terminal_equal"] for r in out["reload"]),
                      "mismatches": len(out["mismatches"])}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["summary"], indent=1))


if __name__ == "__main__":
    main()
