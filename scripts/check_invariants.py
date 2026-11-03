"""Simulator-level invariant checks (run on the actual Isaac Lab environment).

Checks:
  1. Phase ablation: on identical simulator states, observations with and without the explicit phase input
     differ only in channels 42:46, which are exactly zero without it.
  2. Residual bounds: executed residuals never exceed 0.02 m per axis for extreme actions.
  3. No accumulation: a constant action produces the same target offset relative to the nominal target at
     every step (target = nominal + residual, before geometry/workspace limits).
  4. Zero residual reproduces the scripted controllers: compares outcome records of the learned methods with
     zero actions against nominal/geometry, case by case (from pilot_batch output given by --zero-runs).

Usage:
    python scripts/check_invariants.py --num-envs 32 --output outputs/invariants.json [--zero-runs RUNS_DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--num-envs", type=int, default=32)
parser.add_argument("--steps", type=int, default=120)
parser.add_argument("--output", required=True)
parser.add_argument("--zero-runs", default=None, help="pilot_batch output with zero_* and *_dev entries")
add_launcher_args(parser)
args = parser.parse_args()


def compare_zero(runs: Path) -> dict:
    def load(name):
        return {r["case_id"]: r for r in map(json.loads, (runs / name / "episodes.jsonl").read_text().splitlines())}

    out = {}
    for zero, ref in (("zero_residual_vs_nominal", "nominal_dev"), ("zero_combined_vs_geometry", "geometry_dev")):
        a, b = load(zero), load(ref)
        same = sum(a[k]["terminal_reason"] == b[k]["terminal_reason"] for k in a)
        dt = [abs(a[k]["completion_time_s"] - b[k]["completion_time_s"]) for k in a
              if a[k]["success"] and b[k]["success"]]
        out[zero] = {"cases": len(a), "same_terminal_reason": same,
                     "max_completion_time_difference_s": max(dt) if dt else None}
    return out


def main():
    import torch

    from csci645_handover import runtime as rt

    device = args.device if getattr(args, "device", None) else "cuda:0"
    cfg = rt.build_env_cfg("combined", args.num_envs, device, 7, {})
    report = {}
    with launch_simulation(cfg, args):
        from csci645_handover.tasks.handover_env import PHASE_SLICE, HandoverEnv

        env = HandoverEnv(cfg)
        env.reset()
        gen = torch.Generator(device=env.device).manual_seed(0)
        max_phase_diff, max_other_diff, max_resid, accum_err = 0.0, 0.0, 0.0, 0.0
        const = torch.full((env.num_envs, 3), 3.0, device=env.device)
        for k in range(args.steps):
            act = const if k % 2 == 0 else 50.0 * torch.randn(env.num_envs, 3, generator=gen, device=env.device)
            env.step(act)
            env.cfg.phase_input = True
            o_full = env._get_observations()["policy"].clone()
            env.cfg.phase_input = False
            o_mask = env._get_observations()["policy"].clone()
            env.cfg.phase_input = True
            diff = (o_full - o_mask).abs()
            other = torch.cat([diff[:, :PHASE_SLICE.start], diff[:, PHASE_SLICE.stop:]], dim=-1)
            max_other_diff = max(max_other_diff, float(other.max()))
            max_phase_diff = max(max_phase_diff, float(o_mask[:, PHASE_SLICE].abs().max()))
            scored = env.mode == 1
            if scored.any():
                max_resid = max(max_resid, float(env.residual[scored].abs().max()))
                if k % 2 == 0:  # constant action: offset to nominal must equal 0.02 tanh(3) every time
                    expect = 0.02 * torch.tanh(torch.tensor(3.0))
                    accum_err = max(accum_err, float((env.residual[scored] - expect).abs().max()))
        report["phase_ablation"] = {"max_abs_masked_phase_channel": max_phase_diff,
                                    "max_abs_difference_outside_phase_channels": max_other_diff,
                                    "pass": max_phase_diff == 0.0 and max_other_diff == 0.0}
        report["residual_bound"] = {"max_abs_residual_m": max_resid, "pass": max_resid <= 0.02 + 1e-7}
        report["no_accumulation"] = {"max_abs_error_m": accum_err, "pass": accum_err < 1e-6}
        if args.zero_runs:
            z = compare_zero(Path(args.zero_runs))
            report["zero_residual_equivalence"] = z
        report["git"] = rt.git_state()
        report["config_hash"] = rt.config_hash(env.cfg)
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, indent=2, default=str))
        print(json.dumps(report, indent=2, default=str), flush=True)
        env.close()


if __name__ == "__main__":
    main()
