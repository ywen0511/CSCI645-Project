# Robust Bimanual Handover — Geometric Coordination and Residual RL

**Geometric Coordination and Residual Reinforcement Learning for Robust Bimanual Handover**
CSCI 645 Robot Manipulation, Fall 2026 · Yan Wen · Isaac Lab v3.0.0 / Isaac Sim 6.2.0.0 (PhysX) · RSL-RL 5.5.1

Two Franka Panda arms with parallel-jaw grippers hand over a rigid bar in simulation. We compare a nominal
scripted handover, a training-free geometry module (alignment, shared-holding anchor, contact-gated
release), a learned bounded 3-D residual (PPO), their combination, and a phase-input ablation.

## Status: v2 follow-up study complete

| | v1 (original study) | v2 (follow-up: audit, diagnostics, ablations, harder study) |
|---|---|---|
| Source | tag [`experiment-v1`](https://github.com/ywen0511/CSCI645-Project/tree/experiment-v1) | tag [`experiment-v2`](https://github.com/ywen0511/CSCI645-Project/tree/experiment-v2) (experiments); branch [`study/v2-diagnostics`](https://github.com/ywen0511/CSCI645-Project/tree/study/v2-diagnostics) (analysis, report) |
| Release | [v1.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v1.0.0) (unchanged) | [v2.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v2.0.0) |
| Report | [report/report.md](report/report.md) (labels corrected, erratum E1) | [report/v2/report.md](report/v2/report.md) · PDF in the release · [deck](report/v2/deck/deck.pdf) |
| Results | [results/summary](results/summary) | [results/v2/summary/tables.md](results/v2/summary/tables.md) |

Verification of the published v2 release: [docs/v2/RELEASE_VERIFICATION.md](docs/v2/RELEASE_VERIFICATION.md).
Machine-readable status: [STATUS.json](STATUS.json).

## v2 findings

Held-out v2 final suite: 12 conditions × 200 fresh cases (training range ±2 cm / ±0.30 s and ±3 cm
extrapolation), 117,600 evaluation episodes, all reconciled (0 invalid resets, 0 infrastructure errors).
Success %, learned methods = mean of 3 seeds (selected checkpoints):

| controller | inside training range (1,800) | extrapolation ±3 cm (600) | all (2,400) |
|---|---|---|---|
| nominal | 80.7 | 18.8 | 65.2 |
| nominal + 9 mm constant | 85.6 | 20.3 | 69.3 |
| residual (PPO) | 95.1 | 45.2 | 82.6 |
| geometry, 1 cm bound (v1 setting) | 97.8 | 74.3 | 91.9 |
| geometry, 1.5 cm bound | 100.0 | 86.2 | 96.5 |
| combined (geometry 1.5 cm + PPO residual) | 100.0 | 84.4 | 96.1 |
| combined_no_phase | 100.0 | 85.2 | 96.3 |
| **geometry 1.5 cm + 10 mm constant** | **100.0** | **97.0** | **99.2** |

1. **Learning on top of strong geometry does not help.** Combined − geometry 1.5 cm: −0.4 pp
   [95% CI −0.8, −0.2]; combined − (geometry + development-tuned constant): −3.2 pp [−4.0, −2.3]
   (−12.6 on extrapolation). Final checkpoints give the same picture (−0.4 / −3.1).
2. **The learned combined residual is a constant bias in the wrong direction** (≈ −1 to −2.4 mm along the
   approach axis, nearly state independent), in v1 and in v2; a positive constant fixes the remaining
   geometry failures (palm hitting the bar end when the object is shifted toward the receiver).
3. **Without geometry, residual RL learns real state-dependent corrections**: +17.4 pp over nominal and
   +13.3 pp over nominal + constant, but it stays far below geometry.
4. **Geometry is mostly alignment**: alignment +18.9 / +24.0 pp (1 / 1.5 cm bound), contact-gated release
   +7.8 / +7.3 pp, shared-holding anchor ≈ 0; larger alignment bounds help monotonically.
5. **The explicit contact-phase input has no effect** (−0.2 pp [−0.6, +0.2]).
6. **v1 audit**: all v1 tables regenerate byte for byte from the released raw records; errata
   ([docs/v2/V1_ERRATA.md](docs/v2/V1_ERRATA.md)): the v1 aggregate labels "1,400 in-range / 400 stress" are
   1,200 non-stress / 600 stress (numbers unchanged); recorded episode returns omit the terminal-step reward
   (logging only); the v1 "untrained" policies are small constant offsets rather than a zero residual.

Limitations: simulation only, privileged state, translation-only perturbations, three seeds, v2 designed
after v1 diagnostics, training range saturated by the stronger geometry; see the report, Section 7.

## Documents

- v2: [PLAN](docs/v2/PLAN.md) · [DECISIONS](docs/v2/DECISIONS.md) (UTC log) · [AUDIT](docs/v2/AUDIT.md) ·
  [V1_ERRATA](docs/v2/V1_ERRATA.md) · [PROTOCOL](docs/v2/PROTOCOL.md) (frozen) · [REPRODUCE](docs/v2/REPRODUCE.md) ·
  [RELEASE_VERIFICATION](docs/v2/RELEASE_VERIFICATION.md) · [diagnostics](report/v2/diagnostics.md) ·
  [geometry ablation](report/v2/geometry_ablation.md) · cluster wrappers [scripts/cluster_v2](scripts/cluster_v2)
- v1 (historical): [PROJECT_SPEC](docs/PROJECT_SPEC.md) · [EXPERIMENTS](docs/EXPERIMENTS.md) ·
  [IMPLEMENTATION](docs/IMPLEMENTATION.md) · [RUNBOOK](docs/RUNBOOK.md) · [RELEASE](docs/RELEASE.md) ·
  [DECISIONS](docs/DECISIONS.md) · [REPRODUCE](docs/REPRODUCE.md) · [RELEASE_VERIFICATION](docs/RELEASE_VERIFICATION.md) ·
  [SETUP_REMOTE](docs/SETUP_REMOTE.md) · proposal in [proposal/](proposal/)

## Execution contracts

The follow-up assignment that this delivery fulfils is archived verbatim in
[docs/v2/ASSIGNMENT.md](docs/v2/ASSIGNMENT.md) (README of commit `a3bb983`). The original v1 execution brief is
the README of commit [`4314a0f`](https://github.com/ywen0511/CSCI645-Project/blob/4314a0fa6aac360b10300ad3cff8739822c128f0/README.md).
Agent working rules: [AGENTS.md](AGENTS.md).
