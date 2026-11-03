"""Re-run one case with a recording camera and write an MP4 plus a provenance sidecar.

Example:
    python scripts/record_video.py --method combined --checkpoint runs/combined_seed11/checkpoints/selected.pt \
        --suite configs/frozen/suites/final.jsonl --case-id final-joint_early_stress-0003 \
        --run-id combined_seed11 --output videos/combined_seed11__final-joint_early_stress-0003.mp4

The camera only renders (Newton Warp ray tracer, which runs on GPUs without RT cores); it does not change
physics, control timing or randomization. The replay runs a single environment, so its outcome can differ
from the batched evaluation record of the same case by GPU floating-point nondeterminism; the sidecar
stores both outcomes (``replay_outcome`` and, if --eval-records is given, ``evaluation_outcome``).
Playback is real time (20 frames per second = control rate). The last frame is the last control step before
the terminal decision (the environment resets immediately after it).
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
parser.add_argument("--checkpoint", default=None)
parser.add_argument("--suite", required=True)
parser.add_argument("--case-id", required=True)
parser.add_argument("--run-id", required=True)
parser.add_argument("--protocol", default="configs/frozen/protocol.json")
parser.add_argument("--eval-records", default=None, help="Evaluation JSONL holding this case's scored record.")
parser.add_argument("--output", required=True)
parser.add_argument("--width", type=int, default=960)
parser.add_argument("--height", type=int, default=540)
parser.add_argument("--settle-frames", action="store_true", help="Also include the reset-settling frames.")
add_launcher_args(parser)
args = parser.parse_args()


def look_at_quat(eye, target):
    """Camera orientation (x, y, z, w) for the 'world' convention (x forward, z up)."""
    import torch

    from isaaclab.utils.math import quat_from_matrix

    eye, target = torch.tensor(eye), torch.tensor(target)
    f = target - eye
    f = f / f.norm()
    up = torch.tensor([0.0, 0.0, 1.0])
    y = torch.linalg.cross(up, f)
    y = y / y.norm()
    z = torch.linalg.cross(f, y)
    return tuple(float(v) for v in quat_from_matrix(torch.stack([f, y, z], dim=-1).unsqueeze(0))[0])


def main():
    import imageio.v2 as imageio
    import numpy as np
    import torch
    from tensordict import TensorDict

    import isaaclab.sim as sim_utils
    from isaaclab.sensors import CameraCfg
    from isaaclab_newton.renderers import NewtonWarpRendererCfg

    from csci645_handover import runtime as rt
    from csci645_handover.core.case_suites import read_suite

    protocol = json.loads(Path(args.protocol).read_text()) if Path(args.protocol).exists() else {}
    cases, s_hash = read_suite(args.suite)
    case = next((c for c in cases if c["case_id"] == args.case_id), None)
    if case is None:
        raise SystemExit(f"case {args.case_id} not in {args.suite}")
    device = args.device if getattr(args, "device", None) else "cuda:0"
    cfg = rt.build_env_cfg(args.method, 1, device, 0, dict(protocol.get("env_overrides", {})))
    eye, target = (0.10, -1.55, 1.05), (0.0, 0.0, 0.42)
    cfg.scene.video_cam = CameraCfg(
        prim_path="{ENV_REGEX_NS}/VideoCam",
        offset=CameraCfg.OffsetCfg(pos=eye, rot=look_at_quat(eye, target), convention="world"),
        data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(focal_length=18.0, clipping_range=(0.05, 6.0)),
        width=args.width, height=args.height, renderer_cfg=NewtonWarpRendererCfg(),
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with launch_simulation(cfg, args):
        from csci645_handover.tasks.handover_env import HandoverEnv

        env = HandoverEnv(cfg)
        policy, ck_sha, infos = None, None, {}
        if args.checkpoint:
            from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper

            from csci645_handover.agents.ppo_cfg import HandoverPPORunnerCfg, apply_ppo_overrides, make_runner

            agent = apply_ppo_overrides(HandoverPPORunnerCfg(), protocol.get("ppo_overrides", {}))
            agent.device = device
            runner, agent = make_runner(RslRlVecEnvWrapper(env, clip_actions=None), agent, log_dir=None)
            infos = runner.load(args.checkpoint, map_location=device) or {}
            ck_sha = rt.sha256_file(args.checkpoint)
            net = runner.get_inference_policy(device=device)

            def policy(obs):
                return net(TensorDict(obs, batch_size=[1]))

        env.set_case_queue([case])
        env.completed_records = []
        obs, _ = env.reset()
        cam = env.scene.sensors["video_cam"]
        frames = []
        zeros = torch.zeros(1, 3, device=env.device)
        steps = 0
        while not env.completed_records and steps < int(env.max_episode_length) + 5:
            with torch.inference_mode():
                act = zeros if policy is None else policy(obs)
            obs, _, _, _, _ = env.step(act)
            steps += 1
            # the env auto-resets right after the terminal step, so a frame grabbed then shows the next reset
            if env.completed_records:
                break
            if int(env.mode[0]) == 1 or args.settle_frames:
                rgb = cam.data.output["rgb"]
                rgb = rgb.torch if hasattr(rgb, "torch") else rgb
                frames.append(rgb[0, ..., :3].detach().cpu().numpy().astype(np.uint8))
        fps = round(1.0 / env.step_dt)
        imageio.mimwrite(out, frames, fps=fps, codec="libx264", quality=8, macro_block_size=8)
        rec = env.completed_records[0] if env.completed_records else None
        sidecar = {
            "video": out.name, "method": args.method, "run_id": args.run_id, "case_id": args.case_id,
            "condition": case["condition"], "requested_offset_xyz_m": case["requested_offset_xyz_m"],
            "release_offset_s": case["release_offset_s"], "checkpoint": args.checkpoint and Path(args.checkpoint).name,
            "checkpoint_sha256": ck_sha, "checkpoint_transitions": infos.get("transitions"),
            "config_hash": rt.config_hash(cfg), "suite_hash": s_hash, "git": rt.git_state(),
            "frames": len(frames), "fps": fps, "playback_speed": 1.0, "renderer": "NewtonWarpRenderer (RGB, direct lighting)",
            "resolution": [args.width, args.height], "camera_eye_m": eye, "camera_target_m": target,
            "replay_outcome": rec and {k: rec[k] for k in ("terminal_reason", "success", "completion_time_s",
                                                           "release_command_time_s", "independent_hold_s")},
            "utc": rt.utc_now(),
        }
        if args.eval_records:
            for r in rt.read_jsonl(args.eval_records):
                if r["case_id"] == args.case_id:
                    sidecar["evaluation_outcome"] = {k: r[k] for k in ("terminal_reason", "success", "completion_time_s")}
                    sidecar["evaluation_record_file"] = Path(args.eval_records).name
            if "evaluation_outcome" in sidecar and sidecar["replay_outcome"]:
                sidecar["replay_matches_evaluation"] = (
                    sidecar["evaluation_outcome"]["terminal_reason"] == sidecar["replay_outcome"]["terminal_reason"])
        out.with_suffix(".json").write_text(json.dumps(sidecar, indent=2, default=str))
        print(json.dumps(sidecar, indent=2, default=str), flush=True)
        env.close()


if __name__ == "__main__":
    main()
