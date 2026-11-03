"""Independent success/failure evaluator (batched), separate from rewards and controllers.

The evaluator consumes raw measured signals only (contacts, poses, gripper widths, controller event
times). It never reads controller-internal "stable" flags to decide success.

Terminal precedence (highest first): infrastructure error, prohibited collision, drop,
release timeout, episode timeout. Success is declared only when no disqualifying event occurs in
the same step.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

# Terminal reason codes (0 = still running).
RUNNING = 0
SUCCESS = 1
INFRA_ERROR = 2
COLLISION = 3
DROP = 4
RELEASE_TIMEOUT = 5
EPISODE_TIMEOUT = 6
INVALID_RESET = 7

REASON_NAMES = {
    RUNNING: "running",
    SUCCESS: "success",
    INFRA_ERROR: "infrastructure_error",
    COLLISION: "prohibited_collision",
    DROP: "drop",
    RELEASE_TIMEOUT: "release_timeout",
    EPISODE_TIMEOUT: "episode_timeout",
    INVALID_RESET: "invalid_reset",
}


@dataclass(frozen=True)
class OutcomeCfg:
    success_hold_s: float = 2.0
    contact_force: float = 0.2
    """Object-filtered finger normal force above which a finger counts as touching the object [N]."""
    table_force: float = 0.2
    """Object-table normal force above which the table supports the object [N]."""
    giver_open_width: float = 0.07
    """Giver finger gap above which the giver gripper counts as open [m] (fully open = 0.08)."""
    drift_tol: float = 0.02
    """Maximum drift of the object position in the receiver hand frame since release [m]."""
    rel_speed_tol: float = 0.05
    """Maximum object speed relative to the receiver TCP while holding [m/s]."""
    drop_height: float = 0.35
    """Object center height below which the object counts as dropped [m]."""
    workspace_radius: float = 0.6
    """Horizontal distance from the handover center beyond which the object counts as lost [m]."""
    collision_force: float = 1.0
    """Prohibited-contact force threshold on monitored robot links [N]."""
    collision_terminal_s: float = 0.25
    """A prohibited contact sustained this long terminates the episode [s]."""
    misalign_tol: float = 0.01
    """Grasp-point error at the nominal grasp time above which ``flag_misaligned_at_grasp`` is set [m]."""
    conflict_tol: float = 0.01
    """Change of giver-receiver TCP separation during shared holding flagged as conflicting motion [m]."""


class OutcomeEvaluator:
    """Per-environment success timer, terminal-reason logic and diagnostic flags."""

    def __init__(self, cfg: OutcomeCfg, num_envs: int, device: str | torch.device):
        self.cfg = cfg
        self.n = num_envs
        self.device = device
        f = lambda: torch.zeros(num_envs, device=device)  # noqa: E731
        b = lambda: torch.zeros(num_envs, dtype=torch.bool, device=device)  # noqa: E731
        nan = lambda: torch.full((num_envs,), float("nan"), device=device)  # noqa: E731
        self.hold_timer = f()
        self.max_hold = f()
        self.collision_timer = f()
        self.collision_count = torch.zeros(num_envs, dtype=torch.long, device=device)
        self.prev_collision = b()
        self.any_collision = b()
        self.reason = torch.zeros(num_envs, dtype=torch.long, device=device)
        self.completion_time = nan()
        self.giver_contact_end_time = nan()
        self.ref_rel_pos = torch.zeros(num_envs, 3, device=device)
        self.ref_set = b()
        self.flag_misaligned = b()
        self.misalign_checked = b()
        self.flag_premature = b()
        self.flag_conflict = b()
        self.shared_ref_sep = torch.zeros(num_envs, 3, device=device)
        self.shared_ref_set = b()
        self.grasp_error_at_grasp = nan()

    def reset(self, env_ids: torch.Tensor) -> None:
        for name in ("hold_timer", "max_hold", "collision_timer"):
            getattr(self, name)[env_ids] = 0.0
        self.collision_count[env_ids] = 0
        for name in ("prev_collision", "any_collision", "ref_set", "flag_misaligned", "misalign_checked",
                     "flag_premature", "flag_conflict", "shared_ref_set"):
            getattr(self, name)[env_ids] = False
        self.reason[env_ids] = RUNNING
        for name in ("completion_time", "giver_contact_end_time", "grasp_error_at_grasp"):
            getattr(self, name)[env_ids] = float("nan")
        self.ref_rel_pos[env_ids] = 0.0
        self.shared_ref_sep[env_ids] = 0.0

    def update(self, s: dict[str, torch.Tensor], active: torch.Tensor, dt: float, t_grasp: float, horizon: float):
        """Advance one control step for envs where ``active`` (scored phase, not yet terminal).

        Required signals in ``s`` (all (N,) unless noted):
            t, finite (bool), released (bool), giver_width, giver_force_l/r, recv_force_l/r, table_force,
            obj_pos (N,3), obj_rel_in_recv (N,3) object position in the receiver hand frame,
            obj_rel_speed, collision_force (max over monitored links), release_timeout (bool),
            recv_stable_at_release (bool, value of the stability proxy at the release command; diagnostic only),
            grasp_error (N,) |grasp point from object - receiver TCP|, giver_tcp (N,3), recv_tcp (N,3),
            handover_center (3,).

        Returns:
            (N,) long tensor of newly terminal reasons (0 where nothing ended this step).
        """
        c = self.cfg
        t = s["t"]
        giver_contact = (s["giver_force_l"] > c.contact_force) | (s["giver_force_r"] > c.contact_force)
        recv_both = (s["recv_force_l"] > c.contact_force) & (s["recv_force_r"] > c.contact_force)
        table = s["table_force"] > c.table_force
        giver_open = s["giver_width"] > c.giver_open_width

        # giver contact end (first loss of giver contact after the release command)
        ended = active & s["released"] & ~giver_contact & torch.isnan(self.giver_contact_end_time)
        self.giver_contact_end_time = torch.where(ended, t, self.giver_contact_end_time)

        # reference relative pose captured at the release command
        newly_rel = active & s["released"] & ~self.ref_set
        self.ref_rel_pos = torch.where(newly_rel.unsqueeze(-1), s["obj_rel_in_recv"], self.ref_rel_pos)
        self.ref_set = self.ref_set | newly_rel
        drift = torch.linalg.norm(s["obj_rel_in_recv"] - self.ref_rel_pos, dim=-1)

        # diagnostics
        check = active & ~self.misalign_checked & (t >= t_grasp - 1e-6)
        self.grasp_error_at_grasp = torch.where(check, s["grasp_error"], self.grasp_error_at_grasp)
        self.flag_misaligned = self.flag_misaligned | (check & (s["grasp_error"] > c.misalign_tol))
        self.misalign_checked = self.misalign_checked | check
        self.flag_premature = self.flag_premature | (newly_rel & ~s["recv_stable_at_release"])
        shared = active & giver_contact & recv_both & ~s["released"]
        sep = s["recv_tcp"] - s["giver_tcp"]
        newly_shared = shared & ~self.shared_ref_set
        self.shared_ref_sep = torch.where(newly_shared.unsqueeze(-1), sep, self.shared_ref_sep)
        self.shared_ref_set = self.shared_ref_set | newly_shared
        sep_change = torch.linalg.norm(sep - self.shared_ref_sep, dim=-1)
        self.flag_conflict = self.flag_conflict | (shared & self.shared_ref_set & (sep_change > c.conflict_tol))

        # collisions
        coll = active & (s["collision_force"] > c.collision_force)
        self.collision_count += (coll & ~self.prev_collision).long()
        self.prev_collision = coll
        self.any_collision = self.any_collision | coll
        self.collision_timer = torch.where(coll, self.collision_timer + dt, torch.zeros_like(self.collision_timer))

        # independent holding
        z_ok = s["obj_pos"][:, 2] > c.drop_height
        hold = (
            s["released"] & giver_open & ~giver_contact & ~table & recv_both & z_ok
            & (drift < c.drift_tol) & (s["obj_rel_speed"] < c.rel_speed_tol)
        )
        self.hold_timer = torch.where(active & hold, self.hold_timer + dt, torch.zeros_like(self.hold_timer))
        self.max_hold = torch.maximum(self.max_hold, self.hold_timer)

        # terminal events
        horiz = torch.linalg.norm(s["obj_pos"][:, :2] - s["handover_center"][:2], dim=-1)
        infra = ~s["finite"]
        collision_term = coll & (self.collision_timer >= c.collision_terminal_s - 1e-6)
        drop = (~z_ok) | (horiz > c.workspace_radius)
        timeout = t >= horizon - 1e-6
        success = self.hold_timer >= c.success_hold_s - 1e-6

        reason = torch.zeros_like(self.reason)
        # assign lowest precedence first so higher precedence overwrites
        reason = torch.where(success, torch.full_like(reason, SUCCESS), reason)
        reason = torch.where(timeout & ~success, torch.full_like(reason, EPISODE_TIMEOUT), reason)
        reason = torch.where(s["release_timeout"], torch.full_like(reason, RELEASE_TIMEOUT), reason)
        reason = torch.where(drop, torch.full_like(reason, DROP), reason)
        reason = torch.where(collision_term, torch.full_like(reason, COLLISION), reason)
        reason = torch.where(infra, torch.full_like(reason, INFRA_ERROR), reason)
        reason = torch.where(active, reason, torch.zeros_like(reason))
        newly_done = reason != RUNNING
        self.completion_time = torch.where(newly_done & (reason == SUCCESS), t, self.completion_time)
        self.reason = torch.where(newly_done, reason, self.reason)
        return reason
