"""V4 in-grasp offset sampling and the calibrated giver reference (independent of Isaac Lab; CPU-testable).

Frames: offsets are expressed in the environment-local world frame (x = bar axis, z = up). The calibration
average is kept in the giver-hand frame and rotated back with the measured giver-hand orientation, so it is
invariant to the (fixed) commanded hand orientation.

Information flow (fairness contract):
* ``GiverCalibrator.update`` receives only deployable quantities: the corrupted translation measurement
  (after bias/noise/delay, before any EMA), the fixed-transform kinematic estimate computed from measured
  giver proprioception and measured object orientation, the measured giver-hand orientation, contact flags
  and the episode frame counter. It never receives the true object translation or the sampled offset.
* Every per-environment buffer is reset with the episode; deterministic retries of an invalid reset restart
  the window.
"""

from __future__ import annotations

import torch


def quat_apply(q: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
    """Rotate vectors ``v`` (N,3) by unit quaternions ``q`` (N,4) in (x, y, z, w) order (Isaac Lab 3.0)."""
    xyz, w = q[..., :3], q[..., 3:4]
    t = 2.0 * torch.linalg.cross(xyz, v, dim=-1)
    return v + w * t + torch.linalg.cross(xyz, t, dim=-1)


def quat_apply_inverse(q: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
    conj = torch.cat([-q[..., :3], q[..., 3:4]], dim=-1)
    return quat_apply(conj, v)


def window_frames(window_s: float, step_dt: float) -> int:
    """Number of control frames in a calibration window (at least 1)."""
    if window_s <= 0:
        raise ValueError("calibration window must be positive")
    return max(1, int(round(window_s / step_dt)))


def sample_train_offsets(n: int, spec: dict | None, generator: torch.Generator, device) -> torch.Tensor:
    """Training draw of in-grasp offsets: per-axis uniform in [low, high], zero with ``clean_probability``.

    spec = {"low_xyz_m": [...], "high_xyz_m": [...], "clean_probability": p}; the symmetric shorthand
    {"bound_xyz_m": [bx, by, bz]} means low = -b, high = +b. The support may be asymmetric because the
    feasible physical range is (the bar cannot sit deeper toward the giver palm than it can toward the receiver).
    """
    if not spec:
        return torch.zeros(n, 3, device=device)
    if "bound_xyz_m" in spec:
        hi = torch.tensor(spec["bound_xyz_m"], dtype=torch.float32, device=device)
        lo = -hi
    else:
        lo = torch.tensor(spec["low_xyz_m"], dtype=torch.float32, device=device)
        hi = torch.tensor(spec["high_xyz_m"], dtype=torch.float32, device=device)
    if (lo > hi).any():
        raise ValueError("grasp offset support needs low <= high")
    u = torch.rand(n, 3, generator=generator, device=device)
    clean = torch.rand(n, generator=generator, device=device) < float(spec.get("clean_probability", 0.0))
    out = lo + u * (hi - lo)
    out[clean] = 0.0
    return out


class GiverCalibrator:
    """Per-environment mean of (measurement - kinematic estimate) over the first ``frames`` scored frames.

    ``update`` must be called once per fresh control frame. ``scored_frame`` is the 0-based index of that frame
    in the scored episode (negative or None during settling). Frames where the giver is not holding (``valid``
    false) are skipped but still consume the window. When the window closes with no valid frame, the offset
    stays zero (the fixed transform is used).
    """

    def __init__(self, n: int, frames: int, device):
        if frames < 1:
            raise ValueError("frames must be >= 1")
        self.frames = frames
        self.sum_h = torch.zeros(n, 3, device=device)
        self.count = torch.zeros(n, dtype=torch.long, device=device)
        self.closed = torch.zeros(n, dtype=torch.bool, device=device)
        self.offset_h = torch.zeros(n, 3, device=device)

    def reset(self, ids) -> None:
        self.sum_h[ids] = 0.0
        self.count[ids] = 0
        self.closed[ids] = False
        self.offset_h[ids] = 0.0

    def update(self, fresh: torch.Tensor, scored_frame: torch.Tensor, valid: torch.Tensor,
               measured: torch.Tensor, kinematic: torch.Tensor, giver_quat: torch.Tensor) -> None:
        in_window = fresh & (scored_frame >= 0) & (scored_frame < self.frames) & ~self.closed
        use = in_window & valid
        d_h = quat_apply_inverse(giver_quat, measured - kinematic)
        self.sum_h = torch.where(use[:, None], self.sum_h + d_h, self.sum_h)
        self.count = self.count + use.long()
        closing = in_window & (scored_frame >= self.frames - 1)
        mean = self.sum_h / self.count.clamp(min=1)[:, None]
        self.offset_h = torch.where((closing & (self.count > 0))[:, None], mean, self.offset_h)
        self.closed = self.closed | closing

    def correction(self, giver_quat: torch.Tensor) -> torch.Tensor:
        """World-frame correction added to the kinematic estimate (zero until the window closes)."""
        return torch.where(self.closed[:, None], quat_apply(giver_quat, self.offset_h), torch.zeros_like(self.offset_h))
