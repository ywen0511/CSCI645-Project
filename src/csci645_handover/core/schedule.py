"""Nominal (script) trajectory and gripper schedule, evaluated per environment in physical seconds.

All times are seconds measured from the end of reset settling ("episode clock"). All positions are
in the environment-local world frame (meters). The receiver approaches the object along
``approach_dir`` (unit vector pointing from the receiver toward the object, e.g. ``-x``).
"""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class NominalSchedule:
    """Timing of the scripted handover (all values in seconds)."""

    t_pregrasp: float = 1.0
    """Receiver reaches the pre-grasp waypoint."""
    t_grasp: float = 2.0
    """Receiver reaches the nominal grasp position."""
    t_close_start: float = 2.0
    """Receiver begins closing its gripper."""
    close_duration: float = 0.8
    """Duration of the receiver finger-target ramp from open to closed."""
    t_release_nominal: float = 2.8
    """Nominal giver release request time; the actual request is ``t_release_nominal + delta_t``."""
    retreat_delay: float = 0.3
    """Giver retreat starts this long after the *actual* giver release command."""
    retreat_duration: float = 0.7
    """Duration of the giver retreat motion."""
    retreat_distance: float = 0.10
    """Retreat distance along the giver's approach axis (away from the object) [m]."""
    horizon: float = 8.0
    """Scored-episode horizon."""


def min_jerk(s: torch.Tensor) -> torch.Tensor:
    """Minimum-jerk interpolation profile on ``s`` clamped to [0, 1]."""
    s = s.clamp(0.0, 1.0)
    return s**3 * (10.0 - 15.0 * s + 6.0 * s**2)


def receiver_nominal_target(
    t: torch.Tensor,
    start_pos: torch.Tensor,
    pregrasp_pos: torch.Tensor,
    grasp_pos: torch.Tensor,
    sched: NominalSchedule,
) -> torch.Tensor:
    """Nominal receiver TCP position target at episode time ``t``.

    Args:
        t: (N,) episode time [s].
        start_pos, pregrasp_pos, grasp_pos: (N, 3) or (3,) waypoints [m].
        sched: timing.

    Returns:
        (N, 3) target. Segment 1: start->pregrasp over [0, t_pregrasp]; segment 2: pregrasp->grasp over
        [t_pregrasp, t_grasp]; afterwards it holds the grasp position (pre-release and post-release hold).
    """
    t = t.unsqueeze(-1)
    s1 = min_jerk(t / sched.t_pregrasp)
    s2 = min_jerk((t - sched.t_pregrasp) / (sched.t_grasp - sched.t_pregrasp))
    seg1 = start_pos + s1 * (pregrasp_pos - start_pos)
    seg2 = pregrasp_pos + s2 * (grasp_pos - pregrasp_pos)
    return torch.where(t < sched.t_pregrasp, seg1, seg2)


def receiver_finger_target(t: torch.Tensor, open_pos: float, closed_pos: float, sched: NominalSchedule) -> torch.Tensor:
    """Receiver finger joint target (per finger, meters) as a linear ramp from open to closed."""
    s = ((t - sched.t_close_start) / sched.close_duration).clamp(0.0, 1.0)
    return open_pos + s * (closed_pos - open_pos)


def giver_target(
    t: torch.Tensor,
    hold_pos: torch.Tensor,
    release_cmd_time: torch.Tensor,
    retreat_dir: torch.Tensor,
    sched: NominalSchedule,
) -> torch.Tensor:
    """Giver TCP target: hold the (perturbed) start pose, retreat after the actual release command.

    Args:
        t: (N,) episode time.
        hold_pos: (N, 3) giver hold position (already includes the persistent start displacement).
        release_cmd_time: (N,) time of the actual giver release command; ``inf`` if not yet released.
        retreat_dir: (3,) or (N, 3) unit vector of the retreat direction.
    """
    s = min_jerk((t - release_cmd_time - sched.retreat_delay) / sched.retreat_duration)
    s = torch.where(torch.isfinite(release_cmd_time), s, torch.zeros_like(s))
    return hold_pos + (s * sched.retreat_distance).unsqueeze(-1) * retreat_dir
