"""Residual action composition, contact-phase labels and the phase-ablation mask.

Action scaling happens in exactly one place: ``residual = residual_bound * tanh(raw_action)``.
The RSL-RL wrapper is created with ``clip_actions=None`` so no second squashing/clipping is applied.
"""

from __future__ import annotations

import torch

PHASE_NAMES = ("giver_only", "both", "receiver_only", "neither")


def residual_from_action(raw_action: torch.Tensor, bound: float) -> torch.Tensor:
    """Bounded per-axis residual [m] from an unbounded policy output."""
    return bound * torch.tanh(raw_action)


def compose_candidate(p_nominal: torch.Tensor, residual: torch.Tensor, residual_enabled: torch.Tensor) -> torch.Tensor:
    """``p_candidate = p_nominal + residual`` (never accumulated); residual zeroed where disabled."""
    return p_nominal + residual * residual_enabled.unsqueeze(-1).to(residual.dtype)


def contact_phase_onehot(giver_contact: torch.Tensor, receiver_contact: torch.Tensor) -> torch.Tensor:
    """Explicit 4-way one-hot label from *measured* raw contacts: giver only, both, receiver only, neither."""
    g, r = giver_contact.bool(), receiver_contact.bool()
    idx = torch.where(g & ~r, 0, torch.where(g & r, 1, torch.where(~g & r, 2, 3)))
    return torch.nn.functional.one_hot(idx, 4).to(torch.float32)


def apply_phase_mask(obs: torch.Tensor, phase_slice: slice, phase_input: bool) -> torch.Tensor:
    """Zero exactly the explicit phase channels when ``phase_input`` is False (before normalization)."""
    if phase_input:
        return obs
    obs = obs.clone()
    obs[:, phase_slice] = 0.0
    return obs
