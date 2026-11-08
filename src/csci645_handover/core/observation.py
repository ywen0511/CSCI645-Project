"""V3 translation sensor and observation history, independent of Isaac Lab.

Noise is indexed by episode seed and sensor frame, never by vector-environment slot
or global RNG consumption. This pairs exogenous errors across controllers/batch sizes;
it does not promise deterministic PhysX trajectories. All state is per environment.
The environment must pass one monotonically increasing token per control frame.
"""

from __future__ import annotations

import math

import torch


def normal_at(seeds: torch.Tensor, frames: torch.Tensor) -> torch.Tensor:
    """Deterministic standard-normal samples (N,3), using a 31-bit integer hash.

    Integer products stay below signed int64 overflow. Floating transcendental
    results can differ slightly across CPU/CUDA; record device/library versions.
    """
    mask = 0x7FFFFFFF
    axis = torch.arange(6, device=seeds.device, dtype=torch.int64)
    x = (seeds[:, None] * 104729 + frames[:, None] * 13007 + axis * 433494437) & mask
    x = ((x ^ (x >> 16)) * 73244475) & mask
    x = ((x ^ (x >> 16)) * 73244475) & mask
    x = x ^ (x >> 16)
    u = (x.to(torch.float64) + 0.5) / (mask + 1)
    return (torch.sqrt(-2 * torch.log(u[:, :3])) * torch.cos(2 * math.pi * u[:, 3:])).float()


class PositionSensor:
    """y[k] = x[max(0,k-delay)] + episode_bias + sigma*normal(seed,k).

    Optional EMA is an estimator applied AFTER corruption. Startup delay repeats
    the first observed truth; no future samples or cross-episode history are used.
    Repeated reads at a token do not advance the noise, delay, or EMA state.
    """

    def __init__(self, n: int, device: str, max_delay: int = 8, alpha: float = 1.0):
        if max_delay < 0 or not 0 < alpha <= 1:
            raise ValueError("max_delay >= 0 and 0 < alpha <= 1 required")
        self.alpha, self.max_delay = alpha, max_delay
        self.bias = torch.zeros(n, 3, device=device)
        self.sigma = torch.zeros(n, device=device)
        self.delay = torch.zeros(n, dtype=torch.long, device=device)
        self.seeds = torch.zeros(n, dtype=torch.long, device=device)
        self.frames = torch.zeros(n, dtype=torch.long, device=device)
        self.token = torch.full((n,), -1, dtype=torch.long, device=device)
        self.ready = torch.zeros(n, dtype=torch.bool, device=device)
        self.buffer = torch.zeros(n, max_delay + 1, 3, device=device)
        self.raw = torch.zeros(n, 3, device=device)
        self.estimate = torch.zeros(n, 3, device=device)

    def reset(self, ids, *, seeds=None, bias=None, sigma=None, delay=None):
        for key, value in (("seeds", seeds), ("bias", bias), ("sigma", sigma), ("delay", delay)):
            if value is not None:
                target = getattr(self, key)
                incoming = torch.as_tensor(value, device=target.device, dtype=target.dtype)
                if key in ("bias", "sigma") and not torch.isfinite(incoming).all():
                    raise ValueError(f"non-finite {key}")
                if key == "sigma" and (incoming < 0).any():
                    raise ValueError("sigma must be nonnegative")
                if key == "delay" and ((incoming < 0) | (incoming > self.max_delay)).any():
                    raise ValueError("delay outside allocated buffer")
                target[ids] = incoming
        self.frames[ids] = 0
        self.token[ids] = -1
        self.ready[ids] = False
        self.buffer[ids] = 0
        self.raw[ids] = 0
        self.estimate[ids] = 0

    def update(self, truth: torch.Tensor, token: int) -> torch.Tensor:
        fresh = self.token != token
        ids = fresh.nonzero(as_tuple=False).flatten()
        if not len(ids):
            return self.estimate
        first = ~self.ready[ids]
        buf = self.buffer[ids].clone()
        buf[:, 1:] = buf[:, :-1].clone()
        buf[:, 0] = truth[ids]
        buf[first] = truth[ids][first, None, :]
        self.buffer[ids] = buf
        delayed = buf[torch.arange(len(ids), device=ids.device), self.delay[ids]]
        raw = delayed + self.bias[ids] + self.sigma[ids, None] * normal_at(self.seeds[ids], self.frames[ids])
        filtered = self.alpha * raw + (1 - self.alpha) * self.estimate[ids]
        self.estimate[ids] = torch.where(first[:, None], raw, filtered)
        self.raw[ids] = raw
        self.frames[ids] += 1
        self.token[ids] = token
        self.ready[ids] = True
        return self.estimate


class ObservationHistory:
    """Oldest-to-newest frame stack with repeat-first padding and reset isolation."""

    def __init__(self, n: int, width: int, length: int, device: str):
        if length < 1:
            raise ValueError("history length must be positive")
        self.data = torch.zeros(n, length, width, device=device)
        self.token = torch.full((n,), -1, dtype=torch.long, device=device)
        self.ready = torch.zeros(n, dtype=torch.bool, device=device)

    def reset(self, ids):
        self.data[ids] = 0
        self.token[ids] = -1
        self.ready[ids] = False

    def update(self, obs: torch.Tensor, token: int) -> torch.Tensor:
        ids = (self.token != token).nonzero(as_tuple=False).flatten()
        if len(ids):
            first = ~self.ready[ids]
            stack = self.data[ids].clone()
            stack[:, :-1] = stack[:, 1:].clone()
            stack[:, -1] = obs[ids]
            stack[first] = obs[ids][first, None, :]
            self.data[ids] = stack
            self.token[ids] = token
            self.ready[ids] = True
        return self.data.flatten(1)
