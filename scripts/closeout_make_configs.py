#!/usr/bin/env python3
"""Generate the frozen closeout evaluation configs (CPU only, standard library).

    python3 scripts/closeout_make_configs.py --checkpoint-index <v2.0.0 download>/checkpoints.json

Writes (repository-relative, deterministic; refuses to overwrite a file with different content unless --force):
  configs/closeout/repeatability.json            Stage 4 frozen design (8 controllers x 2,400 cases x 3 repeats x 2 layouts)
  configs/closeout/matrices/repeatability_b900.json, repeatability_b23.json
  results/closeout/repeatability/run_manifest.json   one task per (batch size, process repeat, controller)
  configs/closeout/verification_replay.json      Stage 7 predeclared replay (first five case IDs of each condition)
  configs/closeout/matrices/verification_replay.json

Controllers and checkpoints are copied from the v2 final matrices (configs/v2/matrices/final/); checkpoint
SHA-256 values come from the v2.0.0 checkpoint index, which is itself covered by the v2.0.0 SHA256SUMS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = "configs/v2/suites/final.jsonl"
PROTOCOL = "configs/v2/frozen/protocol.json"
SEEDS = [11, 22, 33]
PROCESS_SEEDS = [6454101, 6454102, 6454103]
BATCH_SIZES = [900, 23]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(path: Path, obj, force: bool) -> None:
    text = json.dumps(obj, indent=1, sort_keys=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() != text and not force:
        raise SystemExit(f"refusing to overwrite {path.relative_to(ROOT)} with different content (frozen)")
    path.write_text(text)
    print(f"wrote {path.relative_to(ROOT)} sha256={sha(path)[:12]}")


def final_entries() -> dict:
    out = {}
    for f in sorted((ROOT / "configs/v2/matrices/final").glob("final_*.json")):
        if "manifest" in f.name:
            continue
        m = json.loads(f.read_text())
        for e in m["entries"]:
            out[e["id"]] = (f.relative_to(ROOT).as_posix(), e)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint-index", required=True, help="checkpoints.json from the v2.0.0 release")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    ck_index = {e["member"]: e for e in json.loads(Path(a.checkpoint_index).read_text())}
    fin = final_entries()

    def entry(eid: str, role_alias: str | None = None) -> dict:
        src, e = fin[eid]
        e = dict(e)
        out = {"id": eid, "method": e["method"], "overrides": e.get("overrides", {}),
               "archived_entry": eid, "archived_matrix": src}
        for k in ("training_seed", "run_id", "role", "checkpoint_tag", "checkpoint", "group"):
            if k in e:
                out[k] = e[k]
        if e.get("checkpoint"):
            ck = ck_index[e["checkpoint"]]
            if ck.get("superseded"):
                raise SystemExit(f"{eid}: checkpoint is marked superseded")
            out["checkpoint_sha256"] = ck["sha256"]
            out["checkpoint_asset"] = ck["asset"]
        return out

    rep_ids = ["geometry_1p5cm", "const_geometry_1p5cm"] + [f"combined_seed{s}__{r}" for r in ("selected", "final")
                                                             for s in SEEDS]
    rep_entries = [entry(i) for i in rep_ids]
    # Deduplication rule: identical checkpoint bytes + identical controller settings + identical case ordering.
    seen, dedup = {}, []
    for e in rep_entries:
        key = (e["method"], json.dumps(e["overrides"], sort_keys=True), e.get("checkpoint_sha256"))
        if key in seen:
            dedup.append({"entry": e["id"], "alias_of": seen[key]})
        else:
            seen[key] = e["id"]
    if dedup:
        raise SystemExit(f"unexpected duplicates {dedup}: implement aliasing before freezing")

    suite_p, prot_p = ROOT / SUITE, ROOT / PROTOCOL
    n_cases = sum(1 for _ in suite_p.open())
    rep_cfg = {
        "id": "closeout-repeatability-v1",
        "kind": "retrospective robustness check on the already-used v2 final suite (not a held-out confirmatory "
                "experiment); no checkpoint, constant, threshold or reportable subset is selected from it",
        "suite": SUITE, "suite_sha256": sha(suite_p), "cases": n_cases, "case_order": "suite file order",
        "protocol": PROTOCOL, "protocol_sha256": sha(prot_p),
        "checkpoint_source": {"release": "v2.0.0", "index": "checkpoints.json",
                              "note": "checkpoint paths are relative to the extracted v2.0.0 archives (--checkpoint-root)"},
        "process_seeds": PROCESS_SEEDS, "batch_sizes": BATCH_SIZES,
        "inference": "deterministic actor mean (eval_matrix.py at experiment-v2); observation normalisation frozen from the checkpoint",
        "entries": rep_entries,
        "deduplication": {"rule": "merge entries only if checkpoint bytes (SHA-256), controller settings and case "
                                  "ordering are identical", "aliases": dedup,
                          "result": "no duplicates: selected and final checkpoints differ in bytes for every seed, "
                                    "including seeds 22 and 33 whose selected step equals the last periodic step"},
        "scheduled_episodes": len(rep_entries) * n_cases * len(PROCESS_SEEDS) * len(BATCH_SIZES),
        "task_unit": "one fresh simulator process per (batch size, process repeat, controller); same process seed "
                     "for every controller within a repeat",
        "retry_policy": "a failed or incomplete task may be resumed at most 2 times (eval_matrix resumes by case "
                        "ID and rejects hash mismatches); every attempt is recorded",
        "analysis_plan": "docs/closeout/REPEATABILITY_PLAN.md",
        "analysis_script": "scripts/closeout_repeatability.py",
    }
    dump(ROOT / "configs/closeout/repeatability.json", rep_cfg, a.force)
    mats = {}
    for b in BATCH_SIZES:
        mx = {"name": f"closeout_repeatability_b{b}", "suite": SUITE, "num_envs": b, "protocol": PROTOCOL,
              "trace_cases": [],
              "entries": [{k: v for k, v in e.items() if k in ("id", "method", "overrides", "training_seed", "run_id",
                                                               "role", "checkpoint_tag", "checkpoint", "group")}
                          for e in rep_entries]}
        p = ROOT / f"configs/closeout/matrices/repeatability_b{b}.json"
        dump(p, mx, a.force)
        mats[b] = p
    tasks = []
    for b in BATCH_SIZES:
        for r, ps in enumerate(PROCESS_SEEDS, 1):
            for e in rep_entries:
                tasks.append({"task": f"b{b}_r{r}_{e['id']}", "batch_size": b, "repeat": r, "process_seed": ps,
                              "entry": e["id"], "matrix": mats[b].relative_to(ROOT).as_posix(),
                              "matrix_sha256": sha(mats[b]), "output": f"repeatability/b{b}/r{r}/{e['id']}",
                              "scheduled": n_cases})
    dump(ROOT / "results/closeout/repeatability/run_manifest.json",
         {"config": "configs/closeout/repeatability.json", "config_sha256": sha(ROOT / "configs/closeout/repeatability.json"),
          "tasks": tasks, "scheduled_episodes": sum(t["scheduled"] for t in tasks)}, a.force)

    # Stage 7 predeclared replay sample: first five case IDs (suite order) of each of the 12 conditions.
    cases = [json.loads(l) for l in suite_p.open()]
    by_cond = {}
    for c in cases:
        by_cond.setdefault(c["condition"], []).append(c["case_id"])
    sample = [cid for cond in by_cond for cid in by_cond[cond][:5]]
    sample_suite = ROOT / "configs/closeout/suites/verification_replay.jsonl"
    keep = set(sample)
    text = "".join(l for l in suite_p.open() if json.loads(l)["case_id"] in keep)
    sample_suite.parent.mkdir(parents=True, exist_ok=True)
    if sample_suite.exists() and sample_suite.read_text() != text and not a.force:
        raise SystemExit("refusing to overwrite the frozen replay suite")
    sample_suite.write_text(text)
    learned = [f"{m}_seed{s}__{r}" for m in ("residual", "combined", "combined_no_phase") for s in SEEDS
               for r in ("selected", "final")]
    rp_entries = [entry(i) for i in ["nominal", "geometry_1p5cm", "const_nominal", "const_geometry_1p5cm"] + learned]
    rp = {"id": "closeout-verification-replay-v1",
          "rule": "first five case IDs in suite order of each of the 12 final conditions; nominal, geometry 1.5 cm, "
                  "both constant controls (const_nominal matches residual, const_geometry_1p5cm matches combined and "
                  "combined_no_phase), and the selected and final checkpoint of all nine runs",
          "suite_source": SUITE, "suite_source_sha256": sha(suite_p),
          "sample_suite": sample_suite.relative_to(ROOT).as_posix(), "sample_suite_sha256": sha(sample_suite),
          "case_ids": sample, "num_envs": len(sample), "process_seed": 0, "entries": rp_entries,
          "comparison": "terminal reason and success flag vs the archived v2.0.0 final records (batch 900, seed 0); "
                        "reported as observed agreement on this sample, not a population bound"}
    dump(ROOT / "configs/closeout/verification_replay.json", rp, a.force)
    dump(ROOT / "configs/closeout/matrices/verification_replay.json",
         {"name": "closeout_verification_replay", "suite": sample_suite.relative_to(ROOT).as_posix(),
          "num_envs": len(sample), "protocol": PROTOCOL, "trace_cases": [],
          "entries": [{k: v for k, v in e.items() if k in ("id", "method", "overrides", "training_seed", "run_id", "role",
                                                           "checkpoint_tag", "checkpoint", "group")} for e in rp_entries]},
         a.force)


if __name__ == "__main__":
    main()
