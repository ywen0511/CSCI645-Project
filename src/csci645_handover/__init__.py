"""Robust bimanual handover: geometric coordination and residual PPO in Isaac Lab.

Pure-logic modules live in :mod:`csci645_handover.core` and import only ``torch``/``numpy``.
Simulator modules (:mod:`csci645_handover.tasks`) require an Isaac Lab runtime and register the
``CSCI645-Handover-Direct-v0`` task when imported.
"""

__version__ = "0.1.0"
