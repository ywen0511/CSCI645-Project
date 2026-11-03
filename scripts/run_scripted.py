"""Run the training-free controllers (nominal / geometry) on a case list and save raw outcomes.

Examples:
    python scripts/run_scripted.py --method nominal --num-envs 1 --episodes 20 --output outputs/baseline
    python scripts/run_scripted.py --method geometry --suite configs/frozen/suites/development.jsonl \
        --conditions position_stress --num-envs 64 --output outputs/dev_geometry

Units: meters, seconds. Outputs (in --output): episodes.jsonl (one record per case), summary.json,
traces.json (per-step telemetry for --trace cases), run.json (provenance).
If no --suite is given, ``--episodes`` clean (zero-perturbation) cases are generated.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--method", choices=["nominal", "geometry"], default="nominal")
parser.add_argument("--num-envs", type=int, default=1)
parser.add_argument("--episodes", type=int, default=20, help="Clean cases when --suite is not given.")
parser.add_argument("--suite", default=None, help="JSONL case file.")
parser.add_argument("--conditions", default=None, help="Comma-separated condition filter.")
parser.add_argument("--limit", type=int, default=None, help="Use only the first N matching cases.")
parser.add_argument("--case-ids", default=None, help="Comma-separated case IDs to run.")
parser.add_argument("--overrides", default=None, help="JSON file of env cfg overrides (pilot calibration).")
parser.add_argument("--set", action="append", default=[], help="Env cfg override key=json_value (repeatable).")
parser.add_argument("--trace", type=int, default=2, help="Record per-step traces for the first N cases.")
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--output", required=True)
add_launcher_args(parser)
args = parser.parse_args()


def main():
    from csci645_handover import runtime as rt
    from csci645_handover.core.case_suites import read_suite

    overrides = rt.load_overrides(args.overrides)
    for kv in args.set:
        k, v = kv.split("=", 1)
        overrides[k] = json.loads(v)
    if args.suite:
        cases, s_hash = read_suite(args.suite)
        if args.conditions:
            keep = set(args.conditions.split(","))
            cases = [c for c in cases if c["condition"] in keep]
    else:
        cases = [{"case_id": f"adhoc-clean-{i:04d}", "suite": "adhoc", "condition": "clean",
                  "requested_offset_xyz_m": [0.0, 0.0, 0.0], "release_offset_s": 0.0} for i in range(args.episodes)]
        s_hash = None
    if args.case_ids:
        keep_ids = set(args.case_ids.split(","))
        cases = [c for c in cases if c["case_id"] in keep_ids]
    if args.limit:
        cases = cases[: args.limit]
    device = args.device if getattr(args, "device", None) else "cuda:0"
    cfg = rt.build_env_cfg(args.method, args.num_envs, device, args.seed, overrides)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    with launch_simulation(cfg, args):
        from csci645_handover.tasks.handover_env import HandoverEnv

        env = HandoverEnv(cfg)
        trace_ids = {c["case_id"] for c in cases[: args.trace]}
        records, info = rt.run_cases(env, cases, policy=None, trace_case_ids=trace_ids)
        traces = info.pop("traces")
        meta = {
            "method": args.method, "suite": args.suite, "suite_hash": s_hash, "config_hash": rt.config_hash(cfg),
            "git": rt.git_state(), "hardware": rt.hardware_info(), "overrides": overrides, "utc": rt.utc_now(),
            "env_cfg": rt.env_cfg_dict(cfg), **info,
        }
        for r in records:
            r.update(method=args.method, run_id=f"{args.method}-scripted", training_seed=None,
                     checkpoint_sha256=None, suite_hash=s_hash, config_hash=meta["config_hash"],
                     source_commit=meta["git"]["commit"])
        rt.write_jsonl(out / "episodes.jsonl", records)
        (out / "traces.json").write_text(json.dumps(traces))
        (out / "run.json").write_text(json.dumps(meta, indent=2, default=str))
        summary = summarize(records)
        (out / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2))
        env.close()


def summarize(records):
    from collections import Counter, defaultdict

    by = defaultdict(list)
    for r in records:
        by[r["condition"]].append(r)
    out = {}
    for cond, rs in sorted(by.items()):
        valid = [r for r in rs if r["reset_valid"]]
        n = max(1, len(valid))
        out[cond] = {
            "scheduled": len(rs), "valid": len(valid),
            "success_rate": sum(r["success"] for r in valid) / n,
            "drop_rate": sum(r["drop"] for r in valid) / n,
            "collision_episode_rate": sum(r["collision"] for r in valid) / n,
            "terminal_reasons": dict(Counter(r["terminal_reason"] for r in rs)),
            "mean_completion_time_s": (sum(r["completion_time_s"] for r in valid if r["success"]) /
                                       max(1, sum(r["success"] for r in valid))) if any(r["success"] for r in valid) else None,
        }
    return out


if __name__ == "__main__":
    main()
