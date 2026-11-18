"""V5 dynamic in-grasp slip and the continuously re-estimating giver reference (CPU-testable, no Isaac Lab).

Slip mechanism (environment side, physical)
-------------------------------------------
During the scored episode, after the giver's 0.5 s calibration window has closed and before the receiver
grasps, the bar slides along its axis inside the giver's two-finger grip:

* sliding phase ``[onset, onset + duration)``: the giver's finger position target is relaxed so the squeeze
  force drops to about ``grip_force_n`` (the bar is still carried only by finger friction), and an external
  force along the bar axis acts at the bar's centre of mass. The force is regulated (PID, saturated at
  ``force_max_n``) so the bar's in-grasp displacement follows a minimum-jerk profile to the case's target.
* re-grip phase ``[onset + duration, onset + duration + regrip)``: the finger target returns to the normal
  closed command while the regulated force holds the displacement; afterwards the force is zero.

Only forces act on the bar: no pose or velocity is written during the scored phase. Only the bar-axis (x)
component of the force is applied, so the grip alone carries the bar's weight. The in-grasp displacement used
by the regulator and the realized slip come from the simulator state (environment side, never seen by a
controller). The realized slip is the displacement change from slip onset to the end of the re-grip phase.

Re-estimating giver reference (controller side, deployable signals only)
------------------------------------------------------------------------
``TrackingCalibrator`` extends the V4 one-shot ``GiverCalibrator``: after the initial window has closed it
keeps updating the giver-hand-frame estimate of (measured - kinematic) with an exponential moving average on
every fresh frame in which the giver still holds the bar with both fingers. Inputs are the same deployable
quantities as V4 (corrupted translation measurement, measured giver proprioception and object orientation).
"""

from __future__ import annotations

import torch

from .grasp import GiverCalibrator, quat_apply_inverse

AXIS_X = 0


def minjerk(u: torch.Tensor) -> torch.Tensor:
    u = u.clamp(0.0, 1.0)
    return u ** 3 * (10.0 - 15.0 * u + 6.0 * u * u)


def minjerk_rate(u: torch.Tensor) -> torch.Tensor:
    """d minjerk / du (zero outside [0, 1])."""
    inside = (u >= 0.0) & (u <= 1.0)
    uc = u.clamp(0.0, 1.0)
    return torch.where(inside, 30.0 * uc * uc * (1.0 - uc) ** 2, torch.zeros_like(u))


def clamp_cumulative(grasp_x: float, slip_x: float, lo: float, hi: float) -> float:
    """Slip x such that grasp_x + slip_x stays inside the feasible in-grasp range [lo, hi]."""
    return min(max(grasp_x + slip_x, lo), hi) - grasp_x


def sample_train_slip(n: int, spec: dict | None, grasp_x: torch.Tensor, generator: torch.Generator, device):
    """Training slip draw. spec = {"probability": p, "x_uniform": [lo, hi], "onset_uniform": [a, b],
    "duration_s": d, "cumulative_x": [clo, chi]}. Returns (slip_xyz (n, 3), onset (n,), duration (n,)).
    Inactive draws (probability 1 - p) have zero slip."""
    slip = torch.zeros(n, 3, device=device)
    onset = torch.zeros(n, device=device)
    dur = torch.zeros(n, device=device)
    if not spec:
        return slip, onset, dur
    active = torch.rand(n, generator=generator, device=device) < float(spec["probability"])
    lo, hi = spec["x_uniform"]
    x = lo + torch.rand(n, generator=generator, device=device) * (hi - lo)
    clo, chi = spec["cumulative_x"]
    x = (grasp_x + x).clamp(clo, chi) - grasp_x
    a, b = spec["onset_uniform"]
    on = a + torch.rand(n, generator=generator, device=device) * (b - a)
    slip[:, AXIS_X] = torch.where(active, x, torch.zeros_like(x))
    onset[:] = torch.where(active, on, torch.zeros_like(on))
    dur[:] = torch.where(active, torch.full_like(on, float(spec["duration_s"])), torch.zeros_like(on))
    return slip, onset, dur


IDLE_PHASE, SLIDING, REGRIP, DONE = 0, 1, 2, 3


class SlipRegulator:
    """Per-environment slip state machine and bar-axis force regulator (forces in N, lengths in m, time in s)."""

    def __init__(self, n: int, device, *, kp: float, kd: float, ki: float, force_max_n: float, regrip_s: float,
                 tolerance_m: float):
        self.n, self.device = n, device
        self.kp, self.kd, self.ki, self.fmax = kp, kd, ki, force_max_n
        self.regrip_s, self.tol = regrip_s, tolerance_m
        z = lambda *s: torch.zeros(*s, device=device)  # noqa: E731
        self.target = z(n, 3)
        self.onset = z(n)
        self.duration = z(n)
        self.phase = torch.zeros(n, dtype=torch.long, device=device)
        self.d0 = z(n, 3)
        self.prev_s = z(n, 3)
        self.integ = z(n)
        self.prev_valid = torch.zeros(n, dtype=torch.bool, device=device)
        self.realized = z(n, 3)
        self.error = torch.full((n,), float("nan"), device=device)
        self.valid = torch.ones(n, dtype=torch.bool, device=device)
        self.completed = torch.zeros(n, dtype=torch.bool, device=device)
        self.just_completed = torch.zeros(n, dtype=torch.bool, device=device)
        self.force_abs_max = z(n)
        self.min_giver_force = torch.full((n,), float("inf"), device=device)

    @property
    def active(self) -> torch.Tensor:
        return self.duration > 0

    def reset(self, ids, target, onset, duration) -> None:
        self.target[ids] = target
        self.onset[ids] = onset
        self.duration[ids] = duration
        self.phase[ids] = IDLE_PHASE
        self.d0[ids] = 0.0
        self.prev_s[ids] = 0.0
        self.integ[ids] = 0.0
        self.prev_valid[ids] = False
        self.realized[ids] = 0.0
        self.error[ids] = float("nan")
        self.valid[ids] = True
        self.completed[ids] = False
        self.just_completed[ids] = False
        self.force_abs_max[ids] = 0.0
        self.min_giver_force[ids] = float("inf")

    def phase_at(self, t: torch.Tensor) -> torch.Tensor:
        end_slide = self.onset + self.duration
        ph = torch.where(t < self.onset, IDLE_PHASE, torch.where(t < end_slide, SLIDING,
                         torch.where(t < end_slide + self.regrip_s, REGRIP, DONE)))
        return torch.where(self.active, ph, torch.full_like(ph, IDLE_PHASE))

    def step(self, t: torch.Tensor, d: torch.Tensor, scored: torch.Tensor, dt: float) -> torch.Tensor:
        """One physics substep. ``t``: scored time of this substep, ``d``: in-grasp displacement (n, 3),
        ``scored``: envs in the scored phase. Returns the world-frame force (n, 3) to apply to the bar."""
        ph = torch.where(scored, self.phase_at(t), torch.full_like(self.phase, IDLE_PHASE))
        starting = (ph >= SLIDING) & (self.phase == IDLE_PHASE) & scored & ~self.completed
        self.d0 = torch.where(starting[:, None], d, self.d0)
        self.prev_valid = self.prev_valid & ~starting
        s = d - self.d0
        u = ((t - self.onset) / self.duration.clamp(min=1e-6))
        s_ref = self.target[:, AXIS_X] * minjerk(u)
        v_ref = self.target[:, AXIS_X] * minjerk_rate(u) / self.duration.clamp(min=1e-6)
        v = torch.where(self.prev_valid, (s[:, AXIS_X] - self.prev_s[:, AXIS_X]) / dt, torch.zeros_like(s_ref))
        err = s_ref - s[:, AXIS_X]
        regulating = scored & ((ph == SLIDING) | (ph == REGRIP))
        self.integ = torch.where(regulating, self.integ + err * dt, torch.zeros_like(self.integ))
        f = self.kp * err + self.kd * (v_ref - v) + self.ki * self.integ
        f = torch.where(regulating, f.clamp(-self.fmax, self.fmax), torch.zeros_like(f))
        self.force_abs_max = torch.maximum(self.force_abs_max, f.abs())
        finishing = scored & (ph == DONE) & (self.phase != DONE) & self.active & ~self.completed
        self.realized = torch.where(finishing[:, None], s, self.realized)
        e = torch.stack([s[:, 0] - self.target[:, 0], s[:, 2] - self.target[:, 2]], -1).norm(dim=-1)
        self.error = torch.where(finishing, e, self.error)
        self.valid = torch.where(finishing, e <= self.tol, self.valid)
        self.just_completed = self.just_completed | finishing
        self.completed = self.completed | finishing
        self.prev_s = torch.where(regulating[:, None], s, self.prev_s)
        self.prev_valid = self.prev_valid | regulating
        self.phase = torch.where(scored, ph, self.phase)
        out = torch.zeros_like(d)
        out[:, AXIS_X] = f
        return out

    def take_completed(self) -> torch.Tensor:
        """Envs whose slip completed since the last call (cleared on read)."""
        done = self.just_completed.clone()
        self.just_completed[:] = False
        return done


class TrackingCalibrator(GiverCalibrator):
    """V4 one-shot window, then an EMA re-estimate on every later fresh frame with both giver contacts."""

    def __init__(self, n: int, frames: int, device, alpha: float):
        super().__init__(n, frames, device)
        if not 0.0 < alpha <= 1.0:
            raise ValueError("tracking alpha must be in (0, 1]")
        self.alpha = float(alpha)
        self.updates = torch.zeros(n, dtype=torch.long, device=device)

    def reset(self, ids) -> None:
        super().reset(ids)
        self.updates[ids] = 0

    def update(self, fresh, scored_frame, valid, measured, kinematic, giver_quat) -> None:
        was_closed = self.closed.clone()
        super().update(fresh, scored_frame, valid, measured, kinematic, giver_quat)
        track = fresh & was_closed & valid & (scored_frame >= 0)
        d_h = quat_apply_inverse(giver_quat, measured - kinematic)
        self.offset_h = torch.where(track[:, None], (1 - self.alpha) * self.offset_h + self.alpha * d_h, self.offset_h)
        self.updates = self.updates + track.long()
