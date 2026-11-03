"""Evaluate controllers/policies on an explicit case list (no exploration, frozen normalization).

Examples:
    # deterministic controller
    python scripts/evaluate.py --method geometry --suite configs/frozen/suites/final.jsonl \
        --run-id geometry --output results/raw/final
    # one or more checkpoints of a learned run (validation of every candidate in one process)
    python scripts/evaluate.py --method combined --training-seed 11 \
        --checkpoint runs/combined_seed11/checkpoints/step_002000000.pt [more.pt ...] \
        --suite configs/frozen/suites/validation.jsonl --run-id combined_seed11 --output results/raw/validation

Records are appended to ``<output>/<run_id>[__<ckpt-tag>].jsonl``. On restart, existing records are checked
against run/config/suite/checkpoint hashes and completed case IDs are skipped (resume by case ID);
duplicates are rejected. Units: meters, seconds.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--method", required=True,
                    choices=["nominal", "geometry", "residual", "combined", "combined_no_phase"])
parser.add_argument("--checkpoint", nargs="*", default=[], help="Checkpoint file(s) for learned methods.")
parser.add_argument("--training-seed", type=int, default=None)
parser.add_argument("--suite", required=True)
parser.add_argument("--conditions", default=None)
parser.add_argument("--limit", type=int, default=None)
parser.add_argument("--protocol", default="configs/frozen/protocol.json")
parser.add_argument("--run-id", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--num-envs", type=int, default=None, help="Parallel envs (default: min(#cases, 900)).")
parser.add_argument("--trace-cases", default="", help="Comma-separated case IDs to trace.")
parser.add_argument("--seed", type=int, default=0, help="Simulator seed (cases carry their own perturbations).")
add_launcher_args(parser)
args = parser.parse_args()


def main():
    import torch
    from tensordict import TensorDict

    from csci645_handover import runtime as rt
    from csci645_handover.core.case_suites import read_suite

    learned = args.method in ("residual", "combined", "combined_no_phase")
    if learned and not args.checkpoint:
        raise SystemExit("Learned methods need --checkpoint")
    if not learned and args.checkpoint:
        raise SystemExit("Deterministic controllers take no checkpoint")
    protocol = json.loads(Path(args.protocol).read_text()) if Path(args.protocol).exists() else {}
    overrides = dict(protocol.get("env_overrides", {}))
    cases_all, s_hash = read_suite(args.suite)
    if args.conditions:
        keep = set(args.conditions.split(","))
        cases_all = [c for c in cases_all if c["condition"] in keep]
    if args.limit:
        cases_all = cases_all[: args.limit]
    num_envs = args.num_envs or min(len(cases_all), 900)
    device = args.device if getattr(args, "device", None) else "cuda:0"
    cfg = rt.build_env_cfg(args.method, num_envs, device, args.seed, overrides)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    trace_ids = {c for c in args.trace_cases.split(",") if c}

    with launch_simulation(cfg, args):
        from csci645_handover.tasks.handover_env import HandoverEnv

        env = HandoverEnv(cfg)
        c_hash = rt.config_hash(cfg)
        git = rt.git_state()
        runner = None
        if learned:
            from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper

            from csci645_handover.agents.ppo_cfg import HandoverPPORunnerCfg, apply_ppo_overrides, make_runner

            agent = apply_ppo_overrides(HandoverPPORunnerCfg(), protocol.get("ppo_overrides", {}))
            agent.device = device
            wrapped = RslRlVecEnvWrapper(env, clip_actions=None)
            runner, agent = make_runner(wrapped, agent, log_dir=None)

        targets = args.checkpoint if learned else [None]
        for ckpt in targets:
            ck_sha, tag, infos = None, None, {}
            policy = None
            if ckpt:
                ck_sha = rt.sha256_file(ckpt)
                tag = Path(ckpt).stem
                infos = runner.load(ckpt, map_location=device) or {}
                if infos.get("method") not in (None, args.method):
                    raise SystemExit(f"Checkpoint {ckpt} is for method {infos.get('method')}, not {args.method}")
                if infos.get("config_hash") not in (None, c_hash):
                    raise SystemExit(f"Checkpoint config hash {infos.get('config_hash')} != env config hash {c_hash}")
                if infos.get("phase_input") not in (None, cfg.phase_input):
                    raise SystemExit("Checkpoint phase_input does not match the method's observation mask")
                net = runner.get_inference_policy(device=device)

                def policy(obs, net=net):
                    return net(TensorDict(obs, batch_size=[env.num_envs]))

            fname = f"{args.run_id}__{tag}.jsonl" if tag else f"{args.run_id}.jsonl"
            path = out / fname
            existing = rt.read_jsonl(path)
            seen = set()
            for r in existing:
                if r["case_id"] in seen:
                    raise SystemExit(f"Duplicate record for {r['case_id']} in {path}")
                seen.add(r["case_id"])
                for key, val in (("config_hash", c_hash), ("suite_hash", s_hash), ("checkpoint_sha256", ck_sha),
                                 ("run_id", args.run_id), ("method", args.method)):
                    if r.get(key) != val:
                        raise SystemExit(f"Existing record in {path} has {key}={r.get(key)!r}, expected {val!r}")
            todo = [c for c in cases_all if c["case_id"] not in seen]
            print(f"[evaluate] {fname}: {len(existing)} existing, {len(todo)} to run", flush=True)
            if not todo:
                continue
            records, info = rt.run_cases(env, todo, policy=policy, trace_case_ids=trace_ids)
            traces = info.pop("traces")
            for r in records:
                r.update(run_id=args.run_id, method=args.method, training_seed=args.training_seed,
                         checkpoint=tag, checkpoint_sha256=ck_sha, checkpoint_transitions=infos.get("transitions"),
                         suite_hash=s_hash, config_hash=c_hash, source_commit=git["commit"], source_dirty=git["dirty"])
            got = {r["case_id"] for r in records}
            missing = [c["case_id"] for c in todo if c["case_id"] not in got]
            rt.write_jsonl(path, records, append=True)
            meta = {"file": fname, "suite": args.suite, "suite_hash": s_hash, "config_hash": c_hash,
                    "checkpoint": ckpt, "checkpoint_sha256": ck_sha, "git": git, "hardware": rt.hardware_info(),
                    "utc": rt.utc_now(), "missing_cases": missing, **info}
            rt.write_jsonl(out / "eval_runs.jsonl", [meta], append=True)
            if traces:
                (out / f"traces__{fname.replace('.jsonl', '.json')}").write_text(json.dumps(traces))
            if missing:
                print(f"[evaluate] WARNING: {len(missing)} cases did not finish: {missing[:5]}", flush=True)
            n = len(records)
            print(f"[evaluate] {fname}: ran {n}, success={sum(r['success'] for r in records)}/{n} "
                  f"drop={sum(r['drop'] for r in records)} wall={info['wall_s']:.0f}s", flush=True)
            torch.cuda.empty_cache()
        env.close()


if __name__ == "__main__":
    main()
