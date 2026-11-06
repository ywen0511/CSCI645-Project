"""Training-free geometric coordination module (batched, per-environment state).

Three responsibilities (PROJECT_SPEC.md Section 7):

1. Relative-target alignment: before stable receiver contact, add a bounded correction
   ``clamp(k_align * (p_grasp_from_object - p_grasp_nominal), +-align_max)`` to the candidate target.
2. Shared-holding coordination: once the receiver-stability proxy holds, anchor the receiver target at
   its actual grasp position (world frame) and limit how far the candidate's deviation from the
   nominal trajectory (i.e. the residual) may move it: ``p = p_anchor + clamp(p_cand - p_nom, +-sep_tol)``.
   The giver hold target is frozen (it is already static before release in this task).
3. Release gate: release only after the request *and* receiver stability; wait at most ``max_wait``
   seconds beyond the request, then declare ``release_timeout``.

v2 component ablations switch (1) and (2) off independently through ``align_enabled`` / ``anchor_enabled``
and (3) through the ``gate_on`` argument of :func:`release_decision`. Disabled alignment adds zero
correction; disabled anchoring keeps the candidate target; a disabled gate follows the scheduled request.

The release decision for geometry-off methods is the fixed schedule (see :func:`release_decision`).
"""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class StabilityCfg:
    """Receiver-stability proxy thresholds (calibrated in pilot work; see docs/DECISIONS.md)."""

    min_finger_force: float = 0.2
    """Minimum object-filtered normal force on *each* receiver finger [N]."""
    max_rel_lin_speed: float = 0.03
    """Maximum object linear speed relative to the receiver TCP [m/s]."""
    max_rel_ang_speed: float = 0.5
    """Maximum object angular speed relative to the receiver hand [rad/s]."""
    dwell_s: float = 0.15
    """Continuous time the raw condition must hold [s]."""


@dataclass(frozen=True)
class GeometryCfg:
    align_gain: float = 1.0
    """Gain on the object-derived grasp-point error."""
    align_max: float = 0.015
    """Per-axis bound on the alignment correction [m]."""
    sep_tol: float = 0.01
    """Per-axis bound on deviations from the shared-holding anchor [m]."""
    max_wait: float = 1.0
    """Maximum release delay beyond the request [s]."""
    align_enabled: bool = True
    """v2 ablation flag A. False: the alignment correction is exactly zero."""
    anchor_enabled: bool = True
    """v2 ablation flag H. False: never anchor; the executed target stays the (aligned) candidate."""


class StabilityTracker:
    """Continuous-dwell receiver-stability proxy, independent per environment."""

    def __init__(self, cfg: StabilityCfg, num_envs: int, device: str | torch.device):
        self.cfg = cfg
        self.dwell = torch.zeros(num_envs, device=device)
        self.first_stable_time = torch.full((num_envs,), float("nan"), device=device)

    def reset(self, env_ids: torch.Tensor) -> None:
        self.dwell[env_ids] = 0.0
        self.first_stable_time[env_ids] = float("nan")

    def raw(self, f_left: torch.Tensor, f_right: torch.Tensor, rel_lin: torch.Tensor, rel_ang: torch.Tensor):
        c = self.cfg
        return (
            (f_left > c.min_finger_force)
            & (f_right > c.min_finger_force)
            & (rel_lin < c.max_rel_lin_speed)
            & (rel_ang < c.max_rel_ang_speed)
        )

    def update(self, raw: torch.Tensor, t: torch.Tensor, dt: float) -> torch.Tensor:
        """Advance the dwell timer; returns the debounced stable flag."""
        self.dwell = torch.where(raw, self.dwell + dt, torch.zeros_like(self.dwell))
        stable = self.dwell >= self.cfg.dwell_s - 1e-4
        newly = stable & torch.isnan(self.first_stable_time)
        self.first_stable_time = torch.where(newly, t, self.first_stable_time)
        return stable


def release_decision(
    t: torch.Tensor,
    t_request: torch.Tensor,
    released: torch.Tensor,
    stable: torch.Tensor,
    geometry_on: bool,
    max_wait: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return ``(release_now, timeout_now)`` boolean tensors.

    Without geometry the request releases immediately (no contact-based delay). With geometry the
    release happens at the first control step at or after the request with ``stable`` true, and a
    timeout is declared once ``t - t_request > max_wait`` without release. Release never precedes the
    request.
    """
    requested = (t >= t_request - 1e-4) & ~released
    if not geometry_on:
        return requested, torch.zeros_like(requested)
    release_now = requested & stable
    timeout_now = requested & ~stable & (t - t_request > max_wait + 1e-4)
    return release_now, timeout_now


class GeometryCoordinator:
    """Batched target shaping for the receiver (alignment + shared-holding anchor)."""

    def __init__(self, cfg: GeometryCfg, num_envs: int, device: str | torch.device):
        self.cfg = cfg
        self.anchored = torch.zeros(num_envs, dtype=torch.bool, device=device)
        self.anchor_pos = torch.zeros(num_envs, 3, device=device)
        self.anchor_time = torch.full((num_envs,), float("nan"), device=device)

    def reset(self, env_ids: torch.Tensor) -> None:
        self.anchored[env_ids] = False
        self.anchor_pos[env_ids] = 0.0
        self.anchor_time[env_ids] = float("nan")

    def __call__(
        self,
        t: torch.Tensor,
        p_cand: torch.Tensor,
        p_nom: torch.Tensor,
        grasp_from_object: torch.Tensor,
        grasp_nominal: torch.Tensor,
        receiver_tcp: torch.Tensor,
        stable: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        """Compute the executed receiver target.

        Args:
            t: (N,) episode time.
            p_cand: (N, 3) candidate target (nominal + residual).
            p_nom: (N, 3) nominal target at time t.
            grasp_from_object: (N, 3) receiver grasp point computed from the object pose and the fixed
                object-to-receiver grasp transform.
            grasp_nominal: (N, 3) or (3,) nominal receiver grasp position.
            receiver_tcp: (N, 3) measured receiver TCP position.
            stable: (N,) debounced receiver-stability flag.
        """
        c = self.cfg
        if not c.anchor_enabled:
            stable = torch.zeros_like(stable)
        newly = stable & ~self.anchored
        self.anchor_pos = torch.where(newly.unsqueeze(-1), receiver_tcp, self.anchor_pos)
        self.anchor_time = torch.where(newly, t, self.anchor_time)
        self.anchored = self.anchored | newly

        raw_align = c.align_gain * (grasp_from_object - grasp_nominal)
        align = raw_align.clamp(-c.align_max, c.align_max)
        if not c.align_enabled:
            raw_align = torch.zeros_like(raw_align)
            align = torch.zeros_like(align)
        approach_target = p_cand + align

        deviation = p_cand - p_nom
        clamped_dev = deviation.clamp(-c.sep_tol, c.sep_tol)
        anchored_target = self.anchor_pos + clamped_dev

        a = self.anchored.unsqueeze(-1)
        p_exec = torch.where(a, anchored_target, approach_target)
        return {
            "p_exec": p_exec,
            "align_correction": torch.where(a, torch.zeros_like(align), align),
            "align_saturated": (~self.anchored) & (raw_align.abs() > c.align_max + 1e-9).any(-1),
            "shared_saturated": self.anchored & (deviation.abs() > c.sep_tol + 1e-9).any(-1),
            "anchored": self.anchored.clone(),
        }
