"""Development/pilot batch for the training-free controllers in one simulator process.

Each entry of the plan (JSON list) is {"name", "method" (nominal|geometry), "negative_control" (optional),
"suite" (JSONL path, optional), "conditions" (optional list), "clean" (int, optional: N clean cases),
"limit" (optional), "trace" (int, optional), "set" (optional dict of task-level cfg overrides)}.
Method switches and negative controls only change task-level flags that the task reads every step; the
scene/physics configuration is identical for every entry.

Usage:
    python scripts/pilot_batch.py --plan configs/pilot/gate1_plan.json --num-envs 100 --output runs/pilot/gate1
Development cases only; never use the final suite here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--plan", required=True)
parser.add_argument("--num-envs", type=int, default=100)
parser.add_argument("--output", required=True)
parser.add_argument("--set", action="append", default=[], help="Global env cfg override key=json_value.")
add_launcher_args(parser)
args = parser.parse_args()

TASK_FLAGS = ("geometry_enabled", "residual_enabled", "phase_input", "negative_control", "method")


def main():
    from csci645_handover import runtime as rt
    from csci645_handover.core.case_suites import read_suite
    from csci645_handover.tasks.handover_env_cfg import METHODS

    plan = json.loads(Path(args.plan).read_text())
    overrides = {}
    for kv in args.set:
        k, v = kv.split("=", 1)
        overrides[k] = json.loads(v)
    device = args.device if getattr(args, "device", None) else "cuda:0"
    cfg = rt.build_env_cfg("nominal", args.num_envs, device, 0, overrides)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    with launch_simulation(cfg, args):
        from csci645_handover.tasks.handover_env import HandoverEnv

        env = HandoverEnv(cfg)
        base = {k: getattr(env.cfg, k) for k in TASK_FLAGS}
        all_summ = {}
        for entry in plan:
            for k, v in base.items():
                setattr(env.cfg, k, v)
            env.cfg.method = entry["method"]
            for k, v in METHODS[entry["method"]].items():
                setattr(env.cfg, k, v)
            env.cfg.negative_control = entry.get("negative_control", "")
            saved = {}
            for k, v in entry.get("set", {}).items():
                if k not in ("align_gain", "align_max", "sep_tol", "release_max_wait_s", "t_close_start",
                             "close_duration", "t_release_nominal", "stab_dwell_s", "stab_min_finger_force",
                             "stab_max_rel_lin_speed", "stab_max_rel_ang_speed"):
                    raise KeyError(f"{k} cannot be changed inside one process")
                saved[k] = getattr(env.cfg, k)
                setattr(env.cfg, k, v)
            env.refresh_task_parameters()
            if "suite" in entry:
                cases, s_hash = read_suite(entry["suite"])
                if entry.get("conditions"):
                    cases = [c for c in cases if c["condition"] in set(entry["conditions"])]
            else:
                cases = [{"case_id": f"dev-clean-{i:04d}", "suite": "development", "condition": "clean",
                          "requested_offset_xyz_m": [0.0, 0.0, 0.0], "release_offset_s": 0.0}
                         for i in range(entry.get("clean", 20))]
                s_hash = None
            if entry.get("limit"):
                cases = cases[: entry["limit"]]
            trace_ids = {c["case_id"] for c in cases[: entry.get("trace", 2)]}
            records, info = rt.run_cases(env, cases, policy=None, trace_case_ids=trace_ids)
            traces = info.pop("traces")
            d = out / entry["name"]
            d.mkdir(parents=True, exist_ok=True)
            for r in records:
                r.update(method=entry["method"], run_id=entry["name"], negative_control=env.cfg.negative_control,
                         suite_hash=s_hash, config_hash=rt.config_hash(env.cfg))
            rt.write_jsonl(d / "episodes.jsonl", records)
            (d / "traces.json").write_text(json.dumps(traces))
            summ = summarize(records)
            (d / "summary.json").write_text(json.dumps({"entry": entry, "info": info, "summary": summ}, indent=2))
            all_summ[entry["name"]] = summ
            print(f"[pilot] {entry['name']}: " + json.dumps(summ), flush=True)
            for k, v in saved.items():
                setattr(env.cfg, k, v)
            env.refresh_task_parameters()
        (out / "all_summaries.json").write_text(json.dumps({"git": rt.git_state(), "hardware": rt.hardware_info(),
                                                            "env_cfg": rt.env_cfg_dict(env.cfg),
                                                            "summaries": all_summ}, indent=2, default=str))
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
        succ = [r for r in valid if r["success"]]
        out[cond] = {
            "n": len(rs), "valid": len(valid), "success": round(len(succ) / n, 3),
            "drop": round(sum(r["drop"] for r in valid) / n, 3),
            "reasons": dict(Counter(r["terminal_reason"] for r in rs)),
            "t_done": round(sum(r["completion_time_s"] for r in succ) / len(succ), 2) if succ else None,
            "flags": {"mis": sum(r["flag_misaligned_at_grasp"] for r in valid),
                      "pre": sum(r["flag_premature_release"] for r in valid),
                      "con": sum(r["flag_conflicting_motion"] for r in valid)},
            "coll_eps": sum(r["collision"] for r in valid),
            "rel_delay": round(sum(r["release_delay_s"] or 0 for r in valid) / n, 3),
            "align_sat": round(sum(r["geometry_align_saturation_frac"] for r in valid) / n, 3),
        }
    return out


if __name__ == "__main__":
    main()
