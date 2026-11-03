"""Direct-workflow two-Franka handover environment (Isaac Lab 3.0, Isaac Sim PhysX backend).

Per-environment state machine
-----------------------------
``SETTLE``: scripted reset settling, learning disabled. Stage 1 pins the object at its (shifted) start pose
while the giver servos to the shifted hold pose with open fingers; stage 2 closes the giver fingers with the
object still pinned; stage 3 stops pinning, so only the giver's fingers hold the object. At the end of
stage 3 the start is validated (stable two-finger giver contact, no table support, low object speed, no
prohibited contact, realized displacement within tolerance). Invalid starts are retried deterministically
with the same case up to ``reset_max_attempts`` times; afterwards the episode ends as ``invalid_reset``.

``SCORED``: the episode clock ``t`` runs from 0 at the end of settling. No pinning, weld or teleport acts on
the object. The receiver follows the nominal trajectory (+ bounded residual, + geometry when enabled), the
giver holds and releases on request (geometry may defer release until receiver stability, with a cap), and
the independent evaluator decides the outcome.

``IDLE``: evaluation mode only, after an environment's case queue is exhausted; nothing is recorded.

Time semantics: targets at the start of control step k use ``t_k``; the evaluator judges the state after the
step at ``t_{k+1} = t_k + dt``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

import torch

from isaaclab.controllers import DifferentialIKController, DifferentialIKControllerCfg
from isaaclab.envs import DirectRLEnv
from isaaclab.utils.math import axis_angle_from_quat, quat_apply, quat_apply_inverse, quat_conjugate, quat_mul

from ..core import outcomes as oc
from ..core.case_suites import curriculum_stage
from ..core.geometry import GeometryCfg, GeometryCoordinator, StabilityCfg, StabilityTracker, release_decision
from ..core.policy_io import apply_phase_mask, contact_phase_onehot, residual_from_action
from ..core.schedule import NominalSchedule, giver_target, receiver_finger_target, receiver_nominal_target
from .handover_env_cfg import fixed_hand_quat

if TYPE_CHECKING:
    from .handover_env_cfg import HandoverEnvCfg

SETTLE, SCORED, IDLE = 0, 1, 2
PHASE_SLICE = slice(42, 46)


class HandoverEnv(DirectRLEnv):
    cfg: HandoverEnvCfg

    def __init__(self, cfg: HandoverEnvCfg, render_mode: str | None = None, **kwargs):
        super().__init__(cfg, render_mode, **kwargs)
        sc = self.scene
        self.giver, self.recv, self.obj = sc["giver"], sc["receiver"], sc["object"]
        self.table = sc["table"]
        self.table_half_height = float(sc.cfg.table.spawn.size[2]) / 2
        self.table_default_local = torch.tensor(sc.cfg.table.init_state.pos, dtype=torch.float32, device=self.device)
        self.s_glf, self.s_grf = sc.sensors["giver_lf"], sc.sensors["giver_rf"]
        self.s_rlf, self.s_rrf = sc.sensors["recv_lf"], sc.sensors["recv_rf"]
        self.s_obj = sc.sensors["object_contact"]
        self.s_glinks, self.s_rlinks = sc.sensors["giver_links"], sc.sensors["recv_links"]
        dev, n = self.device, self.num_envs
        c = cfg

        # --- indices ---
        self.arm_ids = self.giver.find_joints("panda_joint[1-7]", preserve_order=True)[0]
        self.f1_id = self.giver.find_joints("panda_finger_joint1")[0]
        self.f2_id = self.giver.find_joints("panda_finger_joint2")[0]
        self.hand_idx = self.giver.find_bodies("panda_hand")[0][0]
        self.jac_idx = self.hand_idx - 1 if self.giver.is_fixed_base else self.hand_idx
        self.jac_cols = [j + self.giver.num_base_dofs for j in self.arm_ids]
        self.monitor_g = self._monitored_ids(self.s_glinks)
        self.monitor_r = self._monitored_ids(self.s_rlinks)

        # --- fixed task geometry (env-local) ---
        T = lambda v: torch.tensor(v, dtype=torch.float32, device=dev)  # noqa: E731
        center = T(c.handover_center)
        half = c.object_size[0] / 2
        self.center_local = center
        self.obj_nominal_local = center.clone()
        self.giver_tcp_nominal = center + T([-half + c.grasp_insertion, 0.0, 0.0])
        self.recv_grasp_nominal = center + T([half - c.grasp_insertion, 0.0, 0.0])
        self.recv_grasp_in_obj = T([half - c.grasp_insertion, 0.0, 0.0])  # fixed object-to-receiver grasp point
        self.recv_pregrasp = self.recv_grasp_nominal + T([c.pregrasp_backoff, 0.0, 0.0])
        self.recv_start = self.recv_grasp_nominal + T([c.start_backoff, 0.0, 0.0])
        self.retreat_dir = T([-1.0, 0.0, 0.0])
        self.q_giver = T(fixed_hand_quat(+1.0))
        self.q_recv = T(fixed_hand_quat(-1.0))
        self.tcp_vec = T([0.0, 0.0, c.tcp_offset])
        # nominal object orientation relative to the receiver hand (for the orientation observation)
        self.q_rel_nom = quat_mul(quat_conjugate(self.q_recv), T([0.0, 0.0, 0.0, 1.0]))
        self.recv_box_lo = self.recv_grasp_nominal + T([-0.05, -0.06, -0.06])
        self.recv_box_hi = self.recv_start + T([0.02, 0.06, 0.06])
        self.settle_total = c.settle_pin_s + c.settle_close_s + c.settle_free_s

        # joint seeds (written at reset). Overwritten from cfg if provided.
        self.q_seed_giver = T(getattr(c, "giver_seed_q", None) or self.giver.data.default_joint_pos.torch[0, self.arm_ids].tolist())
        self.q_seed_recv = T(getattr(c, "receiver_seed_q", None) or self.recv.data.default_joint_pos.torch[0, self.arm_ids].tolist())

        # --- controllers ---
        ik_cfg = DifferentialIKControllerCfg(
            command_type="pose", use_relative_mode=False, ik_method="dls",
            joint_limit_avoidance_gain=c.ik_joint_limit_gain, joint_limit_avoidance_margin=0.3,
        )
        self.ik_g = DifferentialIKController(ik_cfg, num_envs=n, device=dev)
        self.ik_r = DifferentialIKController(ik_cfg, num_envs=n, device=dev)
        self.joint_lo = self.giver.data.soft_joint_pos_limits.torch[0, self.arm_ids, 0]
        self.joint_hi = self.giver.data.soft_joint_pos_limits.torch[0, self.arm_ids, 1]
        self.ik_g.set_joint_pos_limits(self.joint_lo, self.joint_hi)
        self.ik_r.set_joint_pos_limits(self.joint_lo, self.joint_hi)
        self.refresh_task_parameters()

        # --- per-env state ---
        z = lambda *s: torch.zeros(*s, device=dev)  # noqa: E731
        zb = lambda: torch.zeros(n, dtype=torch.bool, device=dev)  # noqa: E731
        nan = lambda: torch.full((n,), float("nan"), device=dev)  # noqa: E731
        self.mode = torch.full((n,), SETTLE, dtype=torch.long, device=dev)
        self.settle_t = z(n)
        self.attempt = torch.zeros(n, dtype=torch.long, device=dev)
        self.t = z(n)
        self.k_scored = torch.zeros(n, dtype=torch.long, device=dev)
        self.offset = z(n, 3)
        self.release_offset = z(n)
        self.realized_offset = z(n, 3)
        self.case_index = torch.full((n,), -1, dtype=torch.long, device=dev)
        self.released = zb()
        self.release_cmd_time = torch.full((n,), float("inf"), device=dev)
        self.release_timeout = zb()
        self.stable = zb()
        self.stable_at_release = zb()
        self.raw_action = z(n, 3)
        self.residual = z(n, 3)
        self.prev_residual = z(n, 3)
        self.p_nom = z(n, 3)
        self.p_exec = z(n, 3)
        self.giver_tcp_target = z(n, 3)
        self.finger_target_g = z(n)
        self.finger_target_r = z(n)
        self.align_corr = z(n, 3)
        self.align_sat_steps = z(n)
        self.shared_sat_steps = z(n)
        self.scored_steps = z(n)
        self.residual_abs_sum = z(n)
        self.residual_abs_max = z(n)
        self.exec_minus_cand_sum = z(n)
        self.ended_reason = torch.zeros(n, dtype=torch.long, device=dev)
        self.newly_ended = zb()
        self.reset_fail_bits = torch.zeros(n, dtype=torch.long, device=dev)
        self.reset_offset_err = z(n)
        self.release_request_time = nan()
        self.ep_reward = z(n)
        self.m: dict[str, torch.Tensor] = {}
        self._fd_pos = z(n, 3)
        self._fd_quat = torch.zeros(n, 4, device=dev)
        self._fd_quat[:, 3] = 1.0
        self._fd_lin = z(n, 3)
        self._fd_ang = z(n, 3)
        self._fd_valid = zb()
        self._fd_obj = z(n, 3)
        self._fd_obj_speed = z(n)

        # --- training curriculum / evaluation queue ---
        self.transition_offset = 0
        self.rng = torch.Generator(device=dev)
        self.rng.manual_seed(int(c.seed) if c.seed is not None else 0)
        self.case_queue: list[dict] | None = None
        self.case_ptr = 0
        self.record_episodes = False
        self.completed_records: list[dict] = []
        self.trace_env_ids: list[int] = []
        self.traces: dict[int, list[dict]] = {}
        self.stats = {k: 0 for k in ("episodes", "success", "drop", "collision", "release_timeout", "timeout",
                                     "invalid_reset", "infra_error")}

    # ------------------------------------------------------------------ helpers
    def refresh_task_parameters(self) -> None:
        """(Re)build schedule, stability proxy, geometry module and evaluator from task-level cfg fields."""
        c, n, dev = self.cfg, self.num_envs, self.device
        self.sched = NominalSchedule(
            t_pregrasp=c.t_pregrasp, t_grasp=c.t_grasp, t_close_start=c.t_close_start,
            close_duration=c.close_duration, t_release_nominal=c.t_release_nominal,
            retreat_delay=c.retreat_delay, retreat_duration=c.retreat_duration,
            retreat_distance=c.retreat_distance, horizon=c.horizon_s,
        )
        self.stab = StabilityTracker(
            StabilityCfg(c.stab_min_finger_force, c.stab_max_rel_lin_speed, c.stab_max_rel_ang_speed, c.stab_dwell_s),
            n, dev,
        )
        self.geom = GeometryCoordinator(GeometryCfg(c.align_gain, c.align_max, c.sep_tol, c.release_max_wait_s), n, dev)
        self.evaluator = oc.OutcomeEvaluator(
            oc.OutcomeCfg(
                success_hold_s=c.success_hold_s, contact_force=c.contact_force, table_force=c.table_force,
                giver_open_width=c.giver_open_width, drift_tol=c.drift_tol, rel_speed_tol=c.rel_speed_tol,
                drop_height=c.drop_height, workspace_radius=c.workspace_radius, collision_force=c.collision_force,
                collision_terminal_s=c.collision_terminal_s, misalign_tol=c.misalign_tol, conflict_tol=c.conflict_tol,
            ),
            n, dev,
        )


    def _monitored_ids(self, sensor) -> list[int]:
        names = list(sensor.body_names)
        keep = [i for i, nm in enumerate(names) if nm.startswith("panda_link") and nm != "panda_link0"]
        keep += [i for i, nm in enumerate(names) if nm == "panda_hand"]
        return sorted(keep)

    def set_case_queue(self, cases: list[dict]) -> None:
        """Evaluation mode: each env episode consumes the next case; then the env idles."""
        self.case_queue = list(cases)
        self.case_ptr = 0
        self.record_episodes = True

    def set_transition_offset(self, offset: int) -> None:
        self.transition_offset = int(offset)

    @property
    def transitions(self) -> int:
        return self.transition_offset + int(self.common_step_counter) * self.num_envs

    # ------------------------------------------------------------------ reset
    def _reset_idx(self, env_ids: Sequence[int] | None) -> None:
        if env_ids is None:
            env_ids = torch.arange(self.num_envs, device=self.device)
        env_ids = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)
        super()._reset_idx(env_ids)
        n = len(env_ids)
        if self.case_queue is not None:
            idle = torch.zeros(n, dtype=torch.bool, device=self.device)
            offs = torch.zeros(n, 3, device=self.device)
            rel = torch.zeros(n, device=self.device)
            cidx = torch.full((n,), -1, dtype=torch.long, device=self.device)
            for k in range(n):
                if self.case_ptr < len(self.case_queue):
                    case = self.case_queue[self.case_ptr]
                    offs[k] = torch.tensor(case["requested_offset_xyz_m"], device=self.device)
                    rel[k] = float(case["release_offset_s"])
                    cidx[k] = self.case_ptr
                    self.case_ptr += 1
                else:
                    idle[k] = True
            self.offset[env_ids] = offs
            self.release_offset[env_ids] = rel
            self.case_index[env_ids] = cidx
            self.mode[env_ids] = torch.where(idle, IDLE, SETTLE)
        else:
            frac = min(1.0, self.transitions / max(1, self.cfg.total_transitions))
            stage = curriculum_stage(self.cfg.curriculum, frac)
            b, rb = stage["position_bound_m"], stage["release_offset_bound_s"]
            u = torch.rand(n, 3, generator=self.rng, device=self.device) * 2 - 1
            ur = torch.rand(n, generator=self.rng, device=self.device) * 2 - 1
            self.offset[env_ids] = u * b
            self.release_offset[env_ids] = ur * rb
            self.case_index[env_ids] = -1
            self.mode[env_ids] = SETTLE
        self.attempt[env_ids] = 0
        self.reset_fail_bits[env_ids] = 0
        self._begin_settle(env_ids)
        self.raw_action[env_ids] = 0.0
        self.residual[env_ids] = 0.0
        self.prev_residual[env_ids] = 0.0
        self.ep_reward[env_ids] = 0.0
        self.ended_reason[env_ids] = oc.RUNNING

    def _begin_settle(self, env_ids: torch.Tensor) -> None:
        """(Re)start reset settling for ``env_ids`` with their current case parameters."""
        dev = self.device
        origins = self.scene.env_origins[env_ids]
        n = len(env_ids)
        for robot, q_seed in ((self.giver, self.q_seed_giver), (self.recv, self.q_seed_recv)):
            q = robot.data.default_joint_pos.torch[env_ids].clone()
            q[:, self.arm_ids] = q_seed
            q[:, self.f1_id] = self.cfg.finger_open
            q[:, self.f2_id] = self.cfg.finger_open
            robot.write_joint_position_to_sim_index(position=q, env_ids=env_ids)
            robot.write_joint_velocity_to_sim_index(velocity=torch.zeros_like(q), env_ids=env_ids)
            robot.actuators.target_command.set_position_index(value=q, env_ids=env_ids)
        pose = torch.zeros(n, 7, device=dev)
        pose[:, :3] = origins + self.obj_nominal_local + self.offset[env_ids]
        pose[:, 6] = 1.0
        self.obj.write_root_pose_to_sim_index(root_pose=pose, env_ids=env_ids)
        self.obj.write_root_velocity_to_sim_index(root_velocity=torch.zeros(n, 6, device=dev), env_ids=env_ids)
        self.settle_t[env_ids] = 0.0
        self.t[env_ids] = 0.0
        self.k_scored[env_ids] = 0
        self._fd_valid[env_ids] = False
        self.released[env_ids] = False
        self.release_cmd_time[env_ids] = float("inf")
        self.release_timeout[env_ids] = False
        self.stable[env_ids] = False
        self.stable_at_release[env_ids] = False
        self.release_request_time[env_ids] = self.cfg.t_release_nominal + self.release_offset[env_ids]
        if self.cfg.negative_control == "giver_holds":
            self.release_request_time[env_ids] = float("inf")
        # table pose: default, or (negative control) raised under the object and shifted to -x so that it
        # supports the bar while staying clear of the receiver's fingers; the giver is absent in that control
        tpose = torch.zeros(n, 7, device=dev)
        tpose[:, :3] = origins + self.table_default_local
        tpose[:, 6] = 1.0
        if self.cfg.negative_control == "table_support":
            # (run with a narrow table, cfg.table_size_override, that fits between the two grippers' fingertips)
            top = self.obj_nominal_local[2] + self.offset[env_ids, 2] - self.cfg.object_size[2] / 2
            tpose[:, 0] = origins[:, 0] + self.obj_nominal_local[0] + self.offset[env_ids, 0]
            tpose[:, 2] = origins[:, 2] + top - self.table_half_height
        self.table.write_root_pose_to_sim_index(root_pose=tpose, env_ids=env_ids)
        self.realized_offset[env_ids] = 0.0
        for name in ("align_sat_steps", "shared_sat_steps", "scored_steps", "residual_abs_sum",
                     "residual_abs_max", "exec_minus_cand_sum"):
            getattr(self, name)[env_ids] = 0.0
        self.stab.reset(env_ids)
        self.geom.reset(env_ids)
        self.evaluator.reset(env_ids)

    # ------------------------------------------------------------------ actions
    def _pre_physics_step(self, actions: torch.Tensor) -> None:
        c = self.cfg
        if not torch.isfinite(actions).all():
            actions = torch.nan_to_num(actions, nan=0.0, posinf=0.0, neginf=0.0)
        scored = self.mode == SCORED
        settle = self.mode == SETTLE
        t = self.t
        m = self.m if self.m else self._measure()

        # residual (bounded, relative to the current nominal target; never accumulated)
        self.prev_residual = self.residual.clone()
        self.raw_action = actions.clone()
        enabled = scored & (c.residual_enabled)
        res = residual_from_action(actions, c.residual_bound_m)
        self.residual = torch.where(enabled.unsqueeze(-1), res, torch.zeros_like(res))

        p_nom = receiver_nominal_target(t, self.recv_start, self.recv_pregrasp, self.recv_grasp_nominal, self.sched)
        if c.negative_control == "no_receiver":
            p_nom = self.recv_start.expand_as(p_nom).clone()
        p_cand = p_nom + self.residual
        if c.geometry_enabled:
            out = self.geom(t, p_cand, p_nom, m["grasp_from_obj"], self.recv_grasp_nominal, m["recv_tcp"], self.stable)
            p_exec = out["p_exec"]
            self.align_corr = out["align_correction"]
            self.align_sat_steps += (out["align_saturated"] & scored).float()
            self.shared_sat_steps += (out["shared_saturated"] & scored).float()
        else:
            p_exec = p_cand
            self.align_corr.zero_()
        p_exec = torch.where(settle.unsqueeze(-1) | (self.mode == IDLE).unsqueeze(-1), self.recv_start.expand_as(p_exec), p_exec)
        p_exec = torch.maximum(torch.minimum(p_exec, self.recv_box_hi), self.recv_box_lo)  # common workspace limit
        self.exec_minus_cand_sum += torch.where(scored, (p_exec - p_cand).norm(dim=-1), torch.zeros_like(t))
        self.residual_abs_sum += torch.where(scored, self.residual.abs().max(-1).values, torch.zeros_like(t))
        self.residual_abs_max = torch.maximum(self.residual_abs_max, self.residual.abs().max(-1).values)
        self.scored_steps += scored.float()
        self.p_nom, self.p_exec = p_nom, p_exec

        # release decision (geometry-off: fixed schedule; geometry-on: contact-gated with cap)
        rel_now, to_now = release_decision(
            t, self.release_request_time, self.released, self.stable, c.geometry_enabled, c.release_max_wait_s
        )
        rel_now = rel_now & scored
        self.release_cmd_time = torch.where(rel_now, t, self.release_cmd_time)
        self.stable_at_release = torch.where(rel_now, self.stable, self.stable_at_release)
        self.released = self.released | rel_now
        self.release_timeout = self.release_timeout | (to_now & scored)

        hold = self.giver_tcp_nominal + self.offset
        g_t = giver_target(t, hold, self.release_cmd_time, self.retreat_dir, self.sched)
        self.giver_tcp_target = torch.where(scored.unsqueeze(-1), g_t, hold)

        # fingers
        st = self.settle_t
        g_settle = torch.where(st < c.settle_pin_s - 1e-4, torch.full_like(st, c.finger_open), torch.full_like(st, c.finger_closed))
        g_scored = torch.where(self.released, torch.full_like(t, c.finger_open), torch.full_like(t, c.finger_closed))
        self.finger_target_g = torch.where(scored, g_scored, torch.where(settle, g_settle, torch.full_like(t, c.finger_closed)))
        r_sched = receiver_finger_target(t, c.finger_open, c.finger_closed, self.sched)
        self.finger_target_r = torch.where(scored, r_sched, torch.full_like(t, c.finger_open))
        if c.negative_control == "no_receiver":
            self.finger_target_r = torch.full_like(t, c.finger_open)

        # IK commands (world frame, fixed orientations)
        origins = self.scene.env_origins
        hand_g = self.giver_tcp_target + origins - quat_apply(self.q_giver.expand(self.num_envs, 4), self.tcp_vec.expand(self.num_envs, 3))
        hand_r = self.p_exec + origins - quat_apply(self.q_recv.expand(self.num_envs, 4), self.tcp_vec.expand(self.num_envs, 3))
        self.ik_g.set_command(torch.cat([hand_g, self.q_giver.expand(self.num_envs, 4)], -1))
        self.ik_r.set_command(torch.cat([hand_r, self.q_recv.expand(self.num_envs, 4)], -1))

    def _apply_action(self) -> None:
        for robot, ik, fingers in ((self.giver, self.ik_g, self.finger_target_g), (self.recv, self.ik_r, self.finger_target_r)):
            jac = robot.data.body_link_jacobian_w.torch[:, self.jac_idx, :, self.jac_cols]
            pose = robot.data.body_pose_w.torch[:, self.hand_idx]
            q = robot.data.joint_pos.torch[:, self.arm_ids]
            q_des = ik.compute(pose[:, :3], pose[:, 3:7], jac, q)
            q_des = torch.maximum(torch.minimum(q_des, self.joint_hi), self.joint_lo)
            robot.actuators.target_command.set_position_index(value=q_des, joint_ids=self.arm_ids)
            robot.actuators.target_command.set_position_index(value=fingers.unsqueeze(-1), joint_ids=self.f1_id)
        # settling stages 1-2: hold the object at its start pose (before the scored episode only)
        pin = (self.mode == SETTLE) & (self.settle_t < self.cfg.settle_pin_s + self.cfg.settle_close_s)
        pin = pin | (self.mode == IDLE)
        ids = pin.nonzero(as_tuple=False).squeeze(-1)
        if len(ids) > 0:
            pose = torch.zeros(len(ids), 7, device=self.device)
            pose[:, :3] = self.scene.env_origins[ids] + self.obj_nominal_local + self.offset[ids]
            pose[:, 6] = 1.0
            self.obj.write_root_pose_to_sim_index(root_pose=pose, env_ids=ids)
            self.obj.write_root_velocity_to_sim_index(root_velocity=torch.zeros(len(ids), 6, device=self.device), env_ids=ids)

    # ------------------------------------------------------------------ measurements
    @staticmethod
    def _filtered(sensor) -> torch.Tensor:
        """(N, M) object/table filtered normal force magnitudes for a single-body finger sensor."""
        return sensor.data.normal_force_matrix_w.torch[:, 0].norm(dim=-1)

    def _measure(self, update_fd: bool = False) -> dict[str, torch.Tensor]:
        origins = self.scene.env_origins
        m: dict[str, torch.Tensor] = {}
        for tag, robot in (("giver", self.giver), ("recv", self.recv)):
            pose = robot.data.body_pose_w.torch[:, self.hand_idx]
            m[f"{tag}_hand_quat"] = pose[:, 3:7]
            m[f"{tag}_tcp"] = pose[:, :3] + quat_apply(pose[:, 3:7], self.tcp_vec.expand(self.num_envs, 3)) - origins
            m[f"{tag}_hand_pos"] = pose[:, :3] - origins
            vel = robot.data.body_link_vel_w.torch[:, self.hand_idx]  # velocity of the hand link frame origin
            m[f"{tag}_hand_linvel"], m[f"{tag}_hand_angvel"] = vel[:, :3], vel[:, 3:6]
            jp = robot.data.joint_pos.torch
            m[f"{tag}_width"] = jp[:, self.f1_id[0]] + jp[:, self.f2_id[0]]
        m["recv_q"] = self.recv.data.joint_pos.torch[:, self.arm_ids]
        m["recv_qd"] = self.recv.data.joint_vel.torch[:, self.arm_ids]
        m["obj_pos"] = self.obj.data.root_pos_w.torch - origins
        m["obj_quat"] = self.obj.data.root_quat_w.torch
        m["obj_linvel"] = self.obj.data.root_lin_vel_w.torch
        m["obj_angvel"] = self.obj.data.root_ang_vel_w.torch
        m["grasp_from_obj"] = m["obj_pos"] + quat_apply(m["obj_quat"], self.recv_grasp_in_obj.expand(self.num_envs, 3))
        fg_l, fg_r = self._filtered(self.s_glf), self._filtered(self.s_grf)
        fr_l, fr_r = self._filtered(self.s_rlf), self._filtered(self.s_rrf)
        m["giver_force_l"], m["giver_force_r"] = fg_l[:, 0], fg_r[:, 0]
        m["recv_force_l"], m["recv_force_r"] = fr_l[:, 0], fr_r[:, 0]
        m["table_force"] = self.s_obj.data.normal_force_matrix_w.torch[:, 0, 0].norm(dim=-1)
        # prohibited contacts: arm links/hands with anything; fingers with the table or any non-object body
        finger_table = torch.stack([fg_l[:, 1], fg_r[:, 1], fr_l[:, 1], fr_r[:, 1]], -1).max(-1).values
        unfiltered = []
        for s in (self.s_glf, self.s_grf, self.s_rlf, self.s_rrf):
            net = s.data.net_forces_w.torch[:, 0]
            filt = s.data.force_matrix_w.torch[:, 0].sum(dim=1)
            unfiltered.append((net - filt).norm(dim=-1))
        finger_other = torch.stack(unfiltered, -1).max(-1).values
        link_g = self.s_glinks.data.net_forces_w.torch[:, self.monitor_g].norm(dim=-1).max(-1).values
        link_r = self.s_rlinks.data.net_forces_w.torch[:, self.monitor_r].norm(dim=-1).max(-1).values
        m["collision_force"] = torch.stack([link_g, link_r, finger_table, finger_other], -1).max(-1).values
        # object motion relative to the receiver hand
        # Object motion relative to the receiver hand, by finite differences of the measured poses over one
        # control step. (PhysX-reported velocities of a body squeezed between fingers contain depenetration
        # bias: a static, gripped bar reported ~1 rad/s; see docs/DECISIONS.md.)
        rel_pos_h = quat_apply_inverse(m["recv_hand_quat"], m["obj_pos"] - m["recv_hand_pos"])
        rel_quat_h = quat_mul(quat_conjugate(m["recv_hand_quat"]), m["obj_quat"])
        if update_fd:
            dt = self.step_dt
            d_pos = (rel_pos_h - self._fd_pos) / dt
            dq = quat_mul(quat_conjugate(self._fd_quat), rel_quat_h)
            d_ang = axis_angle_from_quat(dq) / dt
            valid = self._fd_valid.unsqueeze(-1)
            self._fd_lin = torch.where(valid, quat_apply(m["recv_hand_quat"], d_pos), torch.zeros_like(d_pos))
            self._fd_ang = torch.where(valid, quat_apply(m["recv_hand_quat"], d_ang), torch.zeros_like(d_ang))
            self._fd_obj_speed = torch.where(self._fd_valid, (m["obj_pos"] - self._fd_obj).norm(dim=-1) / dt,
                                             torch.zeros_like(self._fd_obj_speed))
            self._fd_pos, self._fd_quat, self._fd_obj = rel_pos_h, rel_quat_h, m["obj_pos"].clone()
            self._fd_valid = torch.ones_like(self._fd_valid)
        m["obj_speed_fd"] = self._fd_obj_speed
        m["obj_rel_linvel"] = self._fd_lin
        m["obj_rel_angvel"] = self._fd_ang
        m["obj_rel_speed"] = self._fd_lin.norm(dim=-1)
        m["obj_rel_angspeed"] = self._fd_ang.norm(dim=-1)
        m["obj_rel_in_recv"] = quat_apply_inverse(m["recv_hand_quat"], m["obj_pos"] - m["recv_tcp"])
        m["grasp_error"] = (m["grasp_from_obj"] - m["recv_tcp"]).norm(dim=-1)
        finite = torch.ones(self.num_envs, dtype=torch.bool, device=self.device)
        for k in ("giver_tcp", "recv_tcp", "obj_pos", "obj_linvel", "recv_q"):
            finite &= torch.isfinite(m[k]).all(-1)
        m["finite"] = finite
        self.m = m
        return m

    # ------------------------------------------------------------------ dones / rewards / obs
    def _get_dones(self) -> tuple[torch.Tensor, torch.Tensor]:
        c = self.cfg
        dt = self.step_dt
        m = self._measure(update_fd=True)
        settle = self.mode == SETTLE
        scored = self.mode == SCORED
        new_reason = torch.zeros(self.num_envs, dtype=torch.long, device=self.device)

        # ---- settling progress and validity ----
        self.settle_t = torch.where(settle, self.settle_t + dt, self.settle_t)
        done_settle = settle & (self.settle_t >= self.settle_total - 1e-4)
        if done_settle.any():
            realized = m["obj_pos"] - self.obj_nominal_local
            checks = torch.stack([
                (m["giver_force_l"] > c.contact_force) & (m["giver_force_r"] > c.contact_force),
                (m["table_force"] <= c.table_force) | (c.negative_control == "table_support"),
                m["obj_pos"][:, 2] > c.drop_height,
                m["obj_speed_fd"] < c.reset_max_obj_speed,
                m["collision_force"] <= c.collision_force,
                (realized - self.offset).norm(dim=-1) < c.reset_offset_tol,
                m["finite"],
            ], dim=-1)
            valid = checks.all(-1)
            fail_bits = ((~checks).long() * (2 ** torch.arange(checks.shape[-1], device=self.device))).sum(-1)
            self.reset_fail_bits = torch.where(done_settle & ~valid, self.reset_fail_bits | fail_bits, self.reset_fail_bits)
            self.reset_offset_err = torch.where(done_settle, (realized - self.offset).norm(dim=-1), self.reset_offset_err)
            ok = done_settle & valid
            self.realized_offset = torch.where(ok.unsqueeze(-1), realized, self.realized_offset)
            self.mode = torch.where(ok, torch.full_like(self.mode, SCORED), self.mode)
            self.t = torch.where(ok, torch.zeros_like(self.t), self.t)
            self.k_scored = torch.where(ok, torch.zeros_like(self.k_scored), self.k_scored)
            bad = done_settle & ~valid
            if bad.any():
                self.attempt = torch.where(bad, self.attempt + 1, self.attempt)
                retry = bad & (self.attempt < c.reset_max_attempts)
                give_up = bad & ~retry
                ids = retry.nonzero(as_tuple=False).squeeze(-1)
                if len(ids) > 0:
                    self._begin_settle(ids)
                new_reason = torch.where(give_up, torch.full_like(new_reason, oc.INVALID_RESET), new_reason)

        # ---- scored phase: stability proxy, evaluator ----
        # exact episode clock from an integer step counter (float accumulation drifted by ~1e-6 s)
        self.k_scored = torch.where(scored, self.k_scored + 1, self.k_scored)
        self.t = torch.where(scored, self.k_scored.to(self.t.dtype) * dt, self.t)
        raw = self.stab.raw(m["recv_force_l"], m["recv_force_r"], m["obj_rel_speed"], m["obj_rel_angspeed"])
        self.stable = self.stab.update(raw & scored, self.t, dt)
        sig = dict(m)
        sig.update(t=self.t, released=self.released, release_timeout=self.release_timeout,
                   recv_stable_at_release=self.stable_at_release, handover_center=self.center_local)
        sig["giver_width"] = m["giver_width"]
        reason = self.evaluator.update(sig, scored, dt, c.misalign_check_time, c.horizon_s)
        new_reason = torch.where(scored & (reason != oc.RUNNING), reason, new_reason)
        self.newly_ended = new_reason != oc.RUNNING
        self.ended_reason = torch.where(self.newly_ended, new_reason, self.ended_reason)
        if self.record_episodes and self.newly_ended.any():
            self._collect_records(self.newly_ended)
        if self.trace_env_ids:
            self._collect_traces()
        self._update_stats(new_reason)
        terminated = self.newly_ended & (new_reason != oc.EPISODE_TIMEOUT)
        time_out = self.newly_ended & (new_reason == oc.EPISODE_TIMEOUT)
        # safety net: DirectRLEnv max length (should never be reached before the task horizon)
        time_out |= (self.episode_length_buf >= self.max_episode_length - 1) & ~terminated
        self.mode = torch.where(self.newly_ended, torch.full_like(self.mode, IDLE), self.mode)
        return terminated, time_out

    def _get_rewards(self) -> torch.Tensor:
        c = self.cfg
        dt = self.step_dt
        m = self.m
        scored = (self.mode == SCORED) | (self.newly_ended & (self.ended_reason != oc.INVALID_RESET))
        approach_phase = scored & ~self.released
        d = m["grasp_error"]
        r_app = c.rew_approach * (1.0 - torch.tanh(d / c.rew_approach_scale)) * approach_phase.float() * dt
        holding = self.evaluator.hold_timer > 0
        r_hold = c.rew_hold * (holding & scored).float() * dt
        reason = torch.where(self.newly_ended, self.ended_reason, torch.zeros_like(self.ended_reason))
        r_term = (
            c.rew_success * (reason == oc.SUCCESS).float()
            + c.rew_drop * (reason == oc.DROP).float()
            + c.rew_collision * (reason == oc.COLLISION).float()
            + c.rew_release_timeout * (reason == oc.RELEASE_TIMEOUT).float()
        )
        b = c.residual_bound_m
        if c.residual_enabled:
            r_res = c.rew_residual_l2 * ((self.residual / b) ** 2).sum(-1) * scored.float() * dt
            r_rate = c.rew_action_rate * (((self.residual - self.prev_residual) / b) ** 2).sum(-1) * scored.float() * dt
        else:
            r_res = torch.zeros_like(r_app)
            r_rate = torch.zeros_like(r_app)
        total = r_app + r_hold + r_term + r_res + r_rate
        self.ep_reward += total
        log = self.extras.setdefault("log", {})
        log["Reward/approach"] = r_app.mean()
        log["Reward/hold"] = r_hold.mean()
        log["Reward/terminal"] = r_term.mean()
        log["Reward/residual_l2"] = r_res.mean()
        log["Reward/action_rate"] = r_rate.mean()
        return total

    def _get_observations(self) -> dict[str, torch.Tensor]:
        c = self.cfg
        m = self.m if self.m else self._measure()
        q_rel = quat_mul(quat_conjugate(m["recv_hand_quat"]), m["obj_quat"])
        q_err = quat_mul(quat_conjugate(self.q_rel_nom.expand_as(q_rel)), q_rel)
        rel_lin = m["obj_rel_linvel"]
        rel_ang = m["obj_rel_angvel"]
        forces = torch.stack([m["giver_force_l"], m["giver_force_r"], m["recv_force_l"], m["recv_force_r"]], -1)
        giver_contact = (m["giver_force_l"] > c.contact_force) | (m["giver_force_r"] > c.contact_force)
        recv_contact = (m["recv_force_l"] > c.contact_force) | (m["recv_force_r"] > c.contact_force)
        q0 = self.q_seed_recv
        obs = torch.cat(
            [
                m["grasp_from_obj"] - m["recv_tcp"],  # 0:3
                axis_angle_from_quat(q_err),  # 3:6
                rel_lin,  # 6:9
                rel_ang,  # 9:12
                m["giver_tcp"] - m["recv_tcp"],  # 12:15
                torch.stack([m["giver_width"], m["recv_width"]], -1),  # 15:17
                torch.tanh(forces / 5.0),  # 17:21
                m["recv_q"] - q0,  # 21:28
                0.1 * m["recv_qd"],  # 28:35
                self.p_nom - m["recv_tcp"],  # 35:38
                (self.t / c.horizon_s).unsqueeze(-1),  # 38:39
                self.residual / c.residual_bound_m,  # 39:42
                contact_phase_onehot(giver_contact, recv_contact),  # 42:46
            ],
            dim=-1,
        )
        obs = torch.nan_to_num(obs, nan=0.0, posinf=0.0, neginf=0.0).clamp(-10.0, 10.0)
        obs = apply_phase_mask(obs, PHASE_SLICE, c.phase_input)
        return {"policy": obs}

    # ------------------------------------------------------------------ logging / records
    def _update_stats(self, reason: torch.Tensor) -> None:
        ended = reason != oc.RUNNING
        if not ended.any():
            return
        r = reason[ended]
        k = int(ended.sum())
        self.stats["episodes"] += k
        for name, code in (("success", oc.SUCCESS), ("drop", oc.DROP), ("collision", oc.COLLISION),
                           ("release_timeout", oc.RELEASE_TIMEOUT), ("timeout", oc.EPISODE_TIMEOUT),
                           ("invalid_reset", oc.INVALID_RESET), ("infra_error", oc.INFRA_ERROR)):
            self.stats[name] += int((r == code).sum())
        log = self.extras.setdefault("log", {})
        for name, code in (("success", oc.SUCCESS), ("drop", oc.DROP), ("release_timeout", oc.RELEASE_TIMEOUT),
                           ("collision", oc.COLLISION), ("timeout", oc.EPISODE_TIMEOUT)):
            log[f"Episode/{name}_rate"] = (r == code).float().mean()

    def _collect_records(self, ended: torch.Tensor) -> None:
        ids = ended.nonzero(as_tuple=False).squeeze(-1).tolist()
        ev = self.evaluator
        cpu = lambda x: x.detach().cpu()  # noqa: E731
        fields = {
            "reason": cpu(self.ended_reason), "case_index": cpu(self.case_index), "t": cpu(self.t),
            "attempt": cpu(self.attempt), "offset": cpu(self.offset), "realized": cpu(self.realized_offset),
            "rel_off": cpu(self.release_offset), "req_t": cpu(self.release_request_time),
            "cmd_t": cpu(self.release_cmd_time), "gce_t": cpu(ev.giver_contact_end_time),
            "stab_t": cpu(self.stab.first_stable_time), "max_hold": cpu(ev.max_hold), "comp_t": cpu(ev.completion_time),
            "coll_any": cpu(ev.any_collision), "coll_n": cpu(ev.collision_count), "f_mis": cpu(ev.flag_misaligned),
            "f_pre": cpu(ev.flag_premature), "f_con": cpu(ev.flag_conflict), "g_err": cpu(ev.grasp_error_at_grasp),
            "a_sat": cpu(self.align_sat_steps), "s_sat": cpu(self.shared_sat_steps), "steps": cpu(self.scored_steps),
            "res_sum": cpu(self.residual_abs_sum), "res_max": cpu(self.residual_abs_max),
            "exc_sum": cpu(self.exec_minus_cand_sum), "ep_rew": cpu(self.ep_reward),
            "rfail": cpu(self.reset_fail_bits), "roff": cpu(self.reset_offset_err),
        }
        check_names = ("giver_contact", "table_support", "height", "object_speed", "prohibited_contact",
                       "offset_tolerance", "finite")
        f = lambda v: None if (v is None or not math.isfinite(float(v))) else float(v)  # noqa: E731
        for i in ids:
            ci = int(fields["case_index"][i])
            if ci < 0:
                continue
            reason = int(fields["reason"][i])
            steps = max(1.0, float(fields["steps"][i]))
            valid = reason != oc.INVALID_RESET
            rec = {
                "case_id": self.case_queue[ci]["case_id"],
                "condition": self.case_queue[ci]["condition"],
                "env_id": int(i),
                "requested_offset_xyz_m": [float(v) for v in fields["offset"][i]],
                "realized_offset_xyz_m": [float(v) for v in fields["realized"][i]] if valid else None,
                "release_offset_s": float(fields["rel_off"][i]),
                "reset_attempts": int(fields["attempt"][i]) + (1 if valid else 0),
                "reset_valid": valid,
                "success": reason == oc.SUCCESS,
                "drop": reason == oc.DROP,
                "collision": bool(fields["coll_any"][i]),
                "collision_count": int(fields["coll_n"][i]),
                "terminal_reason": oc.REASON_NAMES[reason],
                "completion_time_s": f(fields["comp_t"][i]) if reason == oc.SUCCESS else None,
                "episode_duration_s": f(fields["t"][i]) if valid else None,
                "release_request_time_s": f(fields["req_t"][i]) if valid else None,
                "release_command_time_s": f(fields["cmd_t"][i]),
                "giver_contact_end_time_s": f(fields["gce_t"][i]),
                "receiver_stable_time_s": f(fields["stab_t"][i]),
                "independent_hold_s": float(fields["max_hold"][i]),
                "flag_misaligned_at_grasp": bool(fields["f_mis"][i]),
                "flag_premature_release": bool(fields["f_pre"][i]),
                "flag_conflicting_motion": bool(fields["f_con"][i]),
                "grasp_error_at_grasp_m": f(fields["g_err"][i]),
                "geometry_align_saturation_frac": float(fields["a_sat"][i]) / steps,
                "geometry_shared_saturation_frac": float(fields["s_sat"][i]) / steps,
                "residual_abs_mean_m": float(fields["res_sum"][i]) / steps,
                "residual_abs_max_m": float(fields["res_max"][i]),
                "exec_minus_candidate_mean_m": float(fields["exc_sum"][i]) / steps,
                "episode_return": float(fields["ep_rew"][i]),
                "reset_failed_checks": [nm for b, nm in enumerate(check_names) if int(fields["rfail"][i]) >> b & 1],
                "reset_offset_error_m": float(fields["roff"][i]),
            }
            if rec["release_command_time_s"] is not None and rec["release_request_time_s"] is not None:
                rec["release_delay_s"] = rec["release_command_time_s"] - rec["release_request_time_s"]
            else:
                rec["release_delay_s"] = None
            self.completed_records.append(rec)

    def _collect_traces(self) -> None:
        m = self.m
        for i in self.trace_env_ids:
            row = {
                "case_index": int(self.case_index[i]),
                "mode": int(self.mode[i]), "t": float(self.t[i]), "settle_t": float(self.settle_t[i]),
                "obj_pos": m["obj_pos"][i].tolist(), "recv_tcp": m["recv_tcp"][i].tolist(),
                "giver_tcp": m["giver_tcp"][i].tolist(), "p_nom": self.p_nom[i].tolist(),
                "p_exec": self.p_exec[i].tolist(), "residual": self.residual[i].tolist(),
                "raw_action": self.raw_action[i].tolist(), "align_corr": self.align_corr[i].tolist(),
                "giver_force": [float(m["giver_force_l"][i]), float(m["giver_force_r"][i])],
                "recv_force": [float(m["recv_force_l"][i]), float(m["recv_force_r"][i])],
                "table_force": float(m["table_force"][i]), "collision_force": float(m["collision_force"][i]),
                "giver_width": float(m["giver_width"][i]), "recv_width": float(m["recv_width"][i]),
                "finger_cmd_giver": float(self.finger_target_g[i]), "finger_cmd_recv": float(self.finger_target_r[i]),
                "released": bool(self.released[i]), "release_cmd_time": float(self.release_cmd_time[i]),
                "release_request_time": float(self.release_request_time[i]), "stable": bool(self.stable[i]),
                "stab_dwell": float(self.stab.dwell[i]), "hold_timer": float(self.evaluator.hold_timer[i]),
                "obj_rel_speed": float(m["obj_rel_speed"][i]), "grasp_error": float(m["grasp_error"][i]),
                "obj_rel_angspeed": float(m["obj_rel_angspeed"][i]), "obj_angvel": m["obj_angvel"][i].tolist(),
                "recv_hand_angvel": m["recv_hand_angvel"][i].tolist(), "recv_hand_linvel": m["recv_hand_linvel"][i].tolist(),
                "obj_linvel": m["obj_linvel"][i].tolist(), "obj_quat": m["obj_quat"][i].tolist(),
                "anchored": bool(self.geom.anchored[i]), "reason": int(self.ended_reason[i]) if bool(self.newly_ended[i]) else 0,
                "phase": contact_phase_onehot(
                    (m["giver_force_l"][i:i+1] > self.cfg.contact_force) | (m["giver_force_r"][i:i+1] > self.cfg.contact_force),
                    (m["recv_force_l"][i:i+1] > self.cfg.contact_force) | (m["recv_force_r"][i:i+1] > self.cfg.contact_force),
                )[0].argmax().item(),
            }
            self.traces.setdefault(i, []).append(row)
