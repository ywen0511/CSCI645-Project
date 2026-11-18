#!/usr/bin/env python3
"""V5 public-download GPU checks: write matrices + results/v5/jobs/verification.json (manifest) and compare (CPU).

    python3 scripts/v5_verification.py manifest       # after checkpoint selection; before the delivery tag
    python3 -I scripts/v5_verification.py compare --x <extracted release with the outputs> --output fresh_gpu.json

Manifest (run with scripts/v3_jobs.py --runs-root <extracted release>; execution checkout = experiment-v5b, except
the Study A replay which uses experiment-v5a):
  replay_study_a      Study A anchor ema0p2_cal050_a25 (= V4 geometry_calibrated) on 60 held-out cases (first five
                      base cases of each of the 12 conditions), batch 20
  replay60_<entry>    geometry_best (= geometry_tracking) and slip_robust_history_s111 (selected) on the 60-case
                      slip_mixed_id mechanism subset, batch 20
  reload_<profile>    the seed-111 selected checkpoint of every architecture on 7 cases (first case of each condition)
  resume_check_*      two PPO iterations resumed from slip_robust_history_s111/checkpoints/latest.pt (new directory),
                      then an inspection of the counters, optimizer, normalizer and RNG state
Compare: exact case-ID sets, uniqueness, valid resets, slip/sensor/grasp specs, checkpoint SHA-256 and configuration
hashes against the published records; terminal outcomes against the published records (every mismatch listed;
PhysX trajectories can depend on the batch layout).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover import v5_protocol as v5  # noqa: E402

D = ROOT / "configs/v5/verification"
PROFILES = ("slip_robust_ff", "slip_robust_history", "slip_robust_repeat")
RUN = "slip_robust_history_s111"


def jl(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def put(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1) + "\n")
    return str(p.relative_to(ROOT))


def manifest():
    sel = json.loads((ROOT / "results/v5/slip/selection/selection.json").read_text())
    roles = json.loads((ROOT / "configs/v5/slip/development/baseline_selection.json").read_text())["roles"]
    aliases = json.loads((ROOT / "configs/v5/slip/matrices/final_baselines/aliases.json").read_text())["declared_aliases"]
    sa = jl(ROOT / "configs/v5/calibration/suite_heldout.jsonl")
    keep = []
    for c in dict.fromkeys(r["condition"] for r in sa):
        keep += sorted([r for r in sa if r["condition"] == c], key=lambda r: r["base_case_id"])[:5]
    sa_suite = D / "study_a_replay60.jsonl"
    sa_suite.parent.mkdir(parents=True, exist_ok=True)
    sa_suite.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in keep))
    fin = jl(ROOT / "configs/v5/slip/suites/final.jsonl")
    first = {}
    for r in sorted(fin, key=lambda r: r["case_id"]):
        first.setdefault(r["condition"], r)
    rl = D / "reload7.jsonl"
    rl.write_text("".join(json.dumps(first[c], sort_keys=True) + "\n" for c in v5.ORDER))
    amx = json.loads((ROOT / "configs/v5/calibration/matrix_ema0p2.json").read_text())
    tasks = []
    mp = put(D / "replay_study_a.json", {"name": "v5_replay_study_a", "suite": "$DELIVERY/" + str(sa_suite.relative_to(ROOT)),
                                         "num_envs": 20, "protocol": amx["protocol"], "base_overrides": amx["base_overrides"],
                                         "trace_cases": [], "entries": [e for e in amx["entries"] if e["id"] == "ema0p2_cal050_a25"]})
    tasks.append({"id": "replay_study_a", "kind": "isaac", "repo": "experiment-v5a",
                  "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + mp, "--output", "$RUNS/fresh/replay_study_a",
                           "--seed", "6457501"], "inputs": [mp], "outputs": ["$RUNS/fresh/replay_study_a/ema0p2_cal050_a25.jsonl"]})
    best = aliases.get("geometry_best", "geometry_best")
    x = roles[best]
    sys.path.insert(0, str(ROOT / "scripts"))
    from v5_slip_study import mech_base
    mp = put(D / "replay60_geometry_best.json", {
        "name": "v5_replay60_geometry_best", "suite": "$DELIVERY/configs/v5/slip/suites/final_subset60.jsonl", "num_envs": 20,
        "protocol": "configs/v2/protocol.json", "base_overrides": mech_base(x["group"]), "trace_cases": [],
        "entries": [{"id": best, "method": x["method"], "overrides": x["overrides"]}]})
    tasks.append({"id": "replay60_geometry_best", "kind": "isaac", "repo": "experiment-v5b",
                  "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + mp, "--output", "$RUNS/fresh/replay60/geometry_best",
                           "--seed", str(v5.EVAL_SEED)], "inputs": [mp], "outputs": [f"$RUNS/fresh/replay60/geometry_best/{best}.jsonl"]})
    mp = put(D / f"replay60_{RUN}.json", {
        "name": f"v5_replay60_{RUN}", "suite": "$DELIVERY/configs/v5/slip/suites/final_subset60.jsonl", "num_envs": 20,
        "protocol": "configs/v5/slip/training/slip_robust_history.json", "trace_cases": [],
        "entries": [{"id": f"{RUN}__selected", "method": "combined", "training_seed": 111, "role": "selected",
                     "checkpoint": f"{RUN}/checkpoints/{sel[RUN]['selected']}.pt"}]})
    tasks.append({"id": f"replay60_{RUN}", "kind": "isaac", "repo": "experiment-v5b",
                  "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + mp, "--checkpoint-root", "$RUNS/formal/train",
                           "--output", f"$RUNS/fresh/replay60/{RUN}", "--seed", str(v5.EVAL_SEED)],
                  "inputs": [mp], "outputs": [f"$RUNS/fresh/replay60/{RUN}/{RUN}__selected.jsonl"]})
    for prof in PROFILES:
        r = f"{prof}_s111"
        mp = put(D / f"reload_{prof}.json", {
            "name": f"v5_reload_{prof}", "suite": "$DELIVERY/" + str(rl.relative_to(ROOT)), "num_envs": 7,
            "protocol": f"configs/v5/slip/training/{prof}.json", "trace_cases": [],
            "entries": [{"id": f"{r}__selected", "method": "combined", "training_seed": 111, "role": "selected",
                         "checkpoint": f"{r}/checkpoints/{sel[r]['selected']}.pt"}]})
        tasks.append({"id": f"reload_{prof}", "kind": "isaac", "repo": "experiment-v5b",
                      "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + mp, "--checkpoint-root", "$RUNS/formal/train",
                               "--output", f"$RUNS/fresh/reload/{prof}", "--seed", str(v5.EVAL_SEED)],
                      "inputs": [mp], "outputs": [f"$RUNS/fresh/reload/{prof}/{r}__selected.jsonl"]})
    src = f"$RUNS/formal/train/{RUN}/checkpoints/latest.pt"
    out = f"$RUNS/fresh/resume_check/{RUN}"
    tasks.append({"id": "resume_check_train", "kind": "isaac", "repo": "experiment-v5b",
                  "argv": ["scripts/train.py", "--method", "combined", "--seed", "111", "--protocol",
                           "configs/v5/slip/training/slip_robust_history.json", "--run-type", "smoke", "--resume", src,
                           "--transitions", "10092544", "--output", out],
                  "inputs": [], "outputs": [f"{out}/checkpoints/final.pt"]})
    tasks.append({"id": "resume_check_inspect", "kind": "isaac", "repo": "experiment-v5b",
                  "argv": ["scripts/closeout_inspect_ckpt.py", "--before", src, "--after", f"{out}/checkpoints/final.pt",
                           "--expect-iterations", "308", "--expect-transitions", "10092544", "--output",
                           "$RUNS/fresh/resume_check/inspect.json"],
                  "inputs": [], "outputs": ["$RUNS/fresh/resume_check/inspect.json"]})
    for name, repo in (("verification_a", "experiment-v5a"), ("verification", "experiment-v5b")):
        ts = [{k: v for k, v in t.items() if k != "repo"} for t in tasks if t["repo"] == repo]
        p = ROOT / f"results/v5/jobs/{name}.json"
        p.write_text(json.dumps({"name": name, "execution_tag": repo, "tasks": ts}, indent=1) + "\n")
        print(name, len(ts), "tasks")


def compare(X: Path, output: Path):
    aliases = json.loads((ROOT / "configs/v5/slip/matrices/final_baselines/aliases.json").read_text())["declared_aliases"]
    best = aliases.get("geometry_best", "geometry_best")
    checks = [("replay_study_a", X / "fresh/replay_study_a/ema0p2_cal050_a25.jsonl", X / "study_a/primary/ema0p2_cal050_a25.jsonl",
               D / "study_a_replay60.jsonl"),
              ("replay60_geometry_best", X / f"fresh/replay60/geometry_best/{best}.jsonl", X / f"final/baselines/{best}.jsonl",
               ROOT / "configs/v5/slip/suites/final_subset60.jsonl"),
              (f"replay60_{RUN}", X / f"fresh/replay60/{RUN}/{RUN}__selected.jsonl", X / f"final/{RUN}/{RUN}__selected.jsonl",
               ROOT / "configs/v5/slip/suites/final_subset60.jsonl")]
    for prof in PROFILES:
        r = f"{prof}_s111"
        checks.append((f"reload_{prof}", X / f"fresh/reload/{prof}/{r}__selected.jsonl", X / f"final/{r}/{r}__selected.jsonl",
                       D / "reload7.jsonl"))
    out = {"entries": [], "mismatches": []}
    for name, fresh, pub, suite in checks:
        rows = jl(fresh)
        P = {r["case_id"]: r for r in jl(pub)}
        ids = [r["case_id"] for r in rows]
        want = [r["case_id"] for r in jl(suite)]
        spec = lambda r: (r.get("observation_error"), r.get("grasp_offset_requested_xyz_m"), r.get("slip_xyz_m"),  # noqa: E731
                          r.get("slip_onset_s"))
        row = {"entry": name, "cases": len(rows), "unique": len(set(ids)) == len(ids), "id_set_equal": sorted(ids) == sorted(want),
               "invalid_resets": sum(not r["reset_valid"] for r in rows),
               "terminal_equal": sum(r["terminal_reason"] == P[r["case_id"]]["terminal_reason"] for r in rows),
               "success_equal": sum(r["success"] == P[r["case_id"]]["success"] for r in rows),
               "specs_equal": all(spec(r) == spec(P[r["case_id"]]) for r in rows),
               "checkpoint_sha256_equal": all(r.get("checkpoint_sha256") == P[r["case_id"]].get("checkpoint_sha256") for r in rows),
               "config_hash_equal": all(r["config_hash"] == P[r["case_id"]]["config_hash"] for r in rows),
               "controller_hash_equal": all(r["controller_hash"] == P[r["case_id"]]["controller_hash"] for r in rows)}
        out["mismatches"] += [{"entry": name, "case": r["case_id"], "fresh": r["terminal_reason"],
                               "published": P[r["case_id"]]["terminal_reason"]} for r in rows
                              if r["terminal_reason"] != P[r["case_id"]]["terminal_reason"]]
        out["entries"].append(row)
    ins = X / "fresh/resume_check/inspect.json"
    out["resume"] = json.loads(ins.read_text()) if ins.exists() else None
    out["summary"] = {"episodes": sum(r["cases"] for r in out["entries"]),
                      "terminal_equal": sum(r["terminal_equal"] for r in out["entries"]),
                      "mismatches": len(out["mismatches"]), "resume_ok": bool(out["resume"] and out["resume"].get("ok"))}
    out["ok"] = (len(out["entries"]) == 6 and all(r["unique"] and r["id_set_equal"] and r["specs_equal"] and r["checkpoint_sha256_equal"]
                                                   and r["config_hash_equal"] and r["controller_hash_equal"] for r in out["entries"])
                 and out["summary"]["resume_ok"])
    output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({**out["summary"], "ok": out["ok"]}))
    raise SystemExit(0 if out["ok"] else 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["manifest", "compare"])
    ap.add_argument("--x")
    ap.add_argument("--output")
    a = ap.parse_args()
    manifest() if a.stage == "manifest" else compare(Path(a.x), Path(a.output))
