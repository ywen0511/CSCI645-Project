"""Inspect the handover scene: asset bodies/joints, sensor matching, finger geometry, IK seeds.

Usage (headless):
    python scripts/inspect_scene.py --output outputs/inspect_scene.json

Writes a JSON report with: body/joint names, joint limits, contact-sensor body lists, finger collision
bounding boxes in the hand frame (to verify the TCP offset), and differential-IK solutions for the
giver hold pose and the receiver start/grasp poses with fixed orientations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", default="outputs/inspect_scene.json")
parser.add_argument("--steps", type=int, default=600, help="Physics steps of IK convergence per target.")
parser.add_argument("--jl-gain", type=float, default=0.05, help="Null-space joint-limit avoidance gain.")
add_launcher_args(parser)
args = parser.parse_args()


PI = 3.141592653589793
SEEDS = [
    [0.0, -0.569, 0.0, -2.81, 0.0, 3.037, 0.741],
    [0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785],
    [0.0, -0.3, 0.0, -2.2, 0.0, 1.9, 0.785],
    [0.0, -0.3, 0.0, -2.2, 0.0, 1.9, 0.785 - PI / 2],
    [0.0, -0.3, 0.0, -2.2, 0.0, 1.9, 0.785 + PI / 2],
    [0.0, 0.2, 0.0, -2.0, 0.0, 2.2, 0.785],
    [0.0, 0.2, 0.0, -2.0, 0.0, 2.2, 0.785 - PI / 2],
    [0.0, 0.2, 0.0, -2.0, 0.0, 2.2, 0.785 + PI / 2],
    [0.0, 0.0, 0.0, -1.6, PI / 2, 1.6, 0.0],
    [0.0, 0.0, 0.0, -1.6, -PI / 2, 1.6, 0.0],
    [0.0, -0.2, 0.0, -2.4, 0.0, 2.2, -0.785],
    [0.0, 0.4, 0.0, -1.8, 0.0, 2.6, 0.785],
    [1.01, -0.686, -0.939, -2.386, -2.779, 2.648, 1.488],
    [0.0, -0.4, 0.0, -2.3, 0.0, 1.9, 2.356],
    [0.0, -0.4, 0.0, -2.3, 0.0, 1.9, -0.785],
    [0.0, -0.1, 0.0, -2.0, 0.0, 1.9, 2.356],
]
"""Candidate arm joint seeds; each env starts IK from one of them."""


def main():
    import torch

    import isaaclab.sim as sim_utils
    from isaaclab.controllers import DifferentialIKController, DifferentialIKControllerCfg
    from isaaclab.utils import instantiate
    from isaaclab.utils.math import quat_apply

    from csci645_handover.tasks.handover_env_cfg import HAND_PATH, HandoverEnvCfg, fixed_hand_quat

    cfg = HandoverEnvCfg()
    sim_cfg = cfg.sim
    sim_cfg.device = args.device if getattr(args, "device", None) else "cuda:0"
    report: dict = {}
    with launch_simulation(sim_cfg, args):
        sim = sim_utils.SimulationContext(sim_cfg)
        scene_cfg = cfg.scene
        scene_cfg.num_envs = len(SEEDS)
        scene = instantiate(scene_cfg)
        sim.reset()
        dt = sim.get_physics_dt()
        giver, recv, obj = scene["giver"], scene["receiver"], scene["object"]
        report["giver_body_names"] = list(giver.body_names)
        report["giver_joint_names"] = list(giver.joint_names)
        report["joint_pos_limits"] = giver.data.joint_pos_limits.torch[0].tolist()
        report["default_joint_pos"] = giver.data.default_joint_pos.torch[0].tolist()
        report["is_fixed_base"] = bool(giver.is_fixed_base)
        report["num_base_dofs"] = int(giver.num_base_dofs)
        for name in ("giver_lf", "giver_rf", "recv_lf", "recv_rf", "object_contact", "giver_links", "recv_links"):
            s = scene.sensors[name]
            report[f"sensor_{name}_bodies"] = list(s.body_names)

        # finger geometry in the hand frame (bounding boxes of all prims under each finger)
        from pxr import Usd, UsdGeom

        stage = sim_utils.get_current_stage()
        hand_path = f"/World/envs/env_0/Giver/{HAND_PATH}"
        hand_prim = stage.GetPrimAtPath(hand_path)
        cache = UsdGeom.XformCache()
        hand_xf = cache.GetLocalToWorldTransform(hand_prim)
        inv = hand_xf.GetInverse()
        bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.proxy])
        geo = {}
        for finger in ("panda_leftfinger", "panda_rightfinger"):
            prim = stage.GetPrimAtPath(f"{hand_path}/{finger}")
            box = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
            lo, hi = box.GetMin(), box.GetMax()
            corners = []
            for xi in (lo[0], hi[0]):
                for yi in (lo[1], hi[1]):
                    for zi in (lo[2], hi[2]):
                        p = inv.Transform((xi, yi, zi))
                        corners.append([p[0], p[1], p[2]])
            c = torch.tensor(corners)
            geo[finger] = {"min_in_hand": c.min(0).values.tolist(), "max_in_hand": c.max(0).values.tolist()}
            geo[finger]["children"] = [str(ch.GetPath()) for ch in Usd.PrimRange(prim)][:20]
        report["finger_geometry_hand_frame"] = geo

        # IK convergence for fixed-orientation targets
        hand_idx_g = giver.find_bodies("panda_hand")[0][0]
        arm_ids = giver.find_joints("panda_joint[1-7]")[0]
        jac_idx = hand_idx_g - 1 if giver.is_fixed_base else hand_idx_g
        jac_cols = [j + giver.num_base_dofs for j in arm_ids]
        origins = scene.env_origins
        center = torch.tensor(cfg.handover_center, device=sim.device)
        half = cfg.object_size[0] / 2
        giver_tcp = center + torch.tensor([-half + cfg.grasp_insertion, 0.0, 0.0], device=sim.device)
        recv_grasp = center + torch.tensor([half - cfg.grasp_insertion, 0.0, 0.0], device=sim.device)
        recv_start = recv_grasp + torch.tensor([cfg.start_backoff, 0.0, 0.0], device=sim.device)
        q_g = torch.tensor(fixed_hand_quat(+1.0), device=sim.device)
        q_r = torch.tensor(fixed_hand_quat(-1.0), device=sim.device)
        report["giver_hand_quat_xyzw"] = q_g.tolist()
        report["receiver_hand_quat_xyzw"] = q_r.tolist()

        # move the object away so it does not interfere
        far = obj.data.default_root_pose.torch.clone()
        far[:, :3] = origins + torch.tensor([0.0, 0.0, 2.0], device=sim.device)
        obj.write_root_pose_to_sim_index(root_pose=far)

        ik_cfg = DifferentialIKControllerCfg(
            command_type="pose", use_relative_mode=False, ik_method="dls",
            joint_limit_avoidance_gain=args.jl_gain, joint_limit_avoidance_margin=0.3,
        )
        seeds = torch.tensor(SEEDS, device=sim.device)
        n = scene.num_envs
        results = {}

        def slerp(q0, q1, a):
            dot = (q0 * q1).sum(-1, keepdim=True)
            q1 = torch.where(dot < 0, -q1, q1)
            dot = dot.abs().clamp(max=1.0)
            th = torch.acos(dot)
            s = torch.sin(th)
            w0 = torch.where(s > 1e-6, torch.sin((1 - a) * th) / s.clamp(min=1e-6), 1 - a)
            w1 = torch.where(s > 1e-6, torch.sin(a * th) / s.clamp(min=1e-6), a)
            q = w0 * q0 + w1 * q1
            return q / q.norm(dim=-1, keepdim=True)

        tcp_vec = torch.tensor([0.0, 0.0, cfg.tcp_offset], device=sim.device).expand(n, 3)
        for label, robot, tcp, quat in (
            ("giver_hold", giver, giver_tcp, q_g),
            ("receiver_start", recv, recv_start, q_r),
            ("receiver_grasp", recv, recv_grasp, q_r),
        ):
            # every env tries one joint seed; the target ramps from the seed's own pose to the goal
            q_all = robot.data.default_joint_pos.torch.clone()
            if label != "receiver_grasp":  # receiver_grasp continues from the receiver_start solution
                q_all[:, arm_ids] = seeds
                robot.write_joint_position_to_sim_index(position=q_all)
                robot.write_joint_velocity_to_sim_index(velocity=torch.zeros_like(q_all))
                robot.actuators.target_command.set_position_index(value=q_all)
                scene.write_data_to_sim()
                sim.step(render=False)
                scene.update(dt)
            pose0 = robot.data.body_pose_w.torch[:, hand_idx_g].clone()
            tcp0 = pose0[:, :3] + quat_apply(pose0[:, 3:7], tcp_vec)
            goal = tcp.expand(n, 3) + origins
            ik = DifferentialIKController(ik_cfg, num_envs=n, device=sim.device)
            lim_soft = robot.data.soft_joint_pos_limits.torch[0, arm_ids]
            ik.set_joint_pos_limits(lim_soft[:, 0], lim_soft[:, 1])
            ramp = int(args.steps * 0.6)
            for k in range(args.steps):
                a = torch.full((n, 1), min(1.0, (k + 1) / ramp), device=sim.device)
                q_t = slerp(pose0[:, 3:7], quat.expand(n, 4), a)
                tcp_t = tcp0 + a * (goal - tcp0)
                hand_t = tcp_t - quat_apply(q_t, tcp_vec)
                ik.set_command(torch.cat([hand_t, q_t], -1))
                jac = robot.data.body_link_jacobian_w.torch[:, jac_idx, :, jac_cols]
                pose = robot.data.body_pose_w.torch[:, hand_idx_g]
                q = robot.data.joint_pos.torch[:, arm_ids]
                q_des = ik.compute(pose[:, :3], pose[:, 3:7], jac, q)
                robot.actuators.target_command.set_position_index(value=q_des, joint_ids=arm_ids)
                scene.write_data_to_sim()
                sim.step(render=False)
                scene.update(dt)
            pose = robot.data.body_pose_w.torch[:, hand_idx_g]
            tcp_now = pose[:, :3] + quat_apply(pose[:, 3:7], tcp_vec)
            err = (tcp_now - goal).norm(dim=-1)
            qerr = 1 - (pose[:, 3:7] * quat).sum(-1).abs()
            qj = robot.data.joint_pos.torch[:, arm_ids]
            lim = robot.data.soft_joint_pos_limits.torch[0, arm_ids]
            margin = torch.minimum(qj - lim[:, 0], lim[:, 1] - qj).min(-1).values
            score = err + 0.05 * qerr - 0.01 * margin.clamp(max=0.3)
            best = int(torch.argmin(score))
            results[label] = {
                "best_seed_index": best,
                "joint_pos": qj[best].tolist(),
                "tcp_pos_err_m": err.tolist(),
                "quat_err_1_minus_dot": qerr.tolist(),
                "joint_limit_margin_rad": margin.tolist(),
                "target_tcp_local": tcp.tolist(),
            }
            if label == "receiver_start":  # continue from the best start solution in every env
                q_all = robot.data.default_joint_pos.torch.clone()
                q_all[:, arm_ids] = qj[best]
                robot.write_joint_position_to_sim_index(position=q_all)
                robot.write_joint_velocity_to_sim_index(velocity=torch.zeros_like(q_all))
                robot.actuators.target_command.set_position_index(value=q_all)
                scene.write_data_to_sim()
                sim.step(render=False)
                scene.update(dt)
        report["ik"] = results
        # write inside the launch context: closing the Kit app terminates the process
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
