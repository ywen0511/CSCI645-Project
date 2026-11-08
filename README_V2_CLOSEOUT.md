# Robust Bimanual Handover — Geometric Coordination and Residual RL

**CSCI 645 Robot Manipulation, Fall 2026 · Yan Wen** · Isaac Lab v3.0.0 / Isaac Sim 6.2.0.0 (PhysX) · RSL-RL 5.5.1

## Final delivery (v2.1.1): reproducibility and repeatability closeout

The **delivery branch is `study/v2-diagnostics`** (the default branch `main` is historical). The first
closeout release, v2.1.0, stays published but is superseded by v2.1.1: its source-archive inventory lacked
member hashes, so the documented `download` stage failed in the post-publication check
([ERRATA C9](docs/closeout/ERRATA.md)). This closeout preserves every v1/v2 result and adds a corrected,
executable reproduction workflow, scoped wording, and a
supplementary repeatability check of the existing v2 checkpoints. Nothing was retrained.

| | Link |
|---|---|
| Release (self-contained: copies of all v2.0.0 checkpoints/raw records/logs/videos + closeout evidence) | [v2.1.1](https://github.com/ywen0511/CSCI645-Project/releases/tag/v2.1.1) |
| Source tags | [`experiment-v2`](https://github.com/ywen0511/CSCI645-Project/tree/experiment-v2) (simulator code, frozen protocol) · [`closeout-eval-v1`](https://github.com/ywen0511/CSCI645-Project/tree/closeout-eval-v1) (Stage 4 configs/driver) · [`v2.1.1`](https://github.com/ywen0511/CSCI645-Project/tree/v2.1.1) (delivery tools, report/deck sources) |
| Report (Markdown; PDF in the release) | [report/v2/report.md](report/v2/report.md) · supplementary [report/closeout/repeatability.md](report/closeout/repeatability.md) |
| Presentation | [report/v2/deck/deck.pptx](report/v2/deck/deck.pptx) · [deck.pdf](report/v2/deck/deck.pdf) |
| Tables | [results/v2/summary/tables.md](results/v2/summary/tables.md) · [results/closeout/repeatability/](results/closeout/repeatability/) |
| Checkpoint / video / run indices | `checkpoints.json`, `videos.json`, `runs.json`, `manifest.json` in the release |
| Reproduction | [docs/closeout/REPRODUCE.md](docs/closeout/REPRODUCE.md) (driver [`scripts/closeout.py`](scripts/closeout.py)) |
| Verification record | [docs/closeout/VERIFICATION.md](docs/closeout/VERIFICATION.md) |
| Corrections | [docs/closeout/ERRATA.md](docs/closeout/ERRATA.md) · decisions [docs/closeout/DECISIONS.md](docs/closeout/DECISIONS.md) · status [STATUS.json](STATUS.json) |

### Findings (v2 held-out final suite, 2,400 cases; unchanged from v2.0.0)

Success %, learned methods = mean of 3 training seeds (selected checkpoints):
nominal 65.2 · nominal + 9 mm constant 69.3 · residual (PPO) 82.6 · geometry 1.5 cm 96.5 · combined
(geometry 1.5 cm + PPO residual) 96.1 · combined_no_phase 96.3 · **geometry 1.5 cm + 10 mm constant 99.2**.

- In this task and training setup, residual RL on top of strong geometry added no robust value: combined −
  geometry −0.4 pp [−0.8, −0.2], and it lost to geometry plus a development-tuned constant (−3.2 pp
  [−4.0, −2.3]). This is scoped to the evaluated task, controller, reward, PPO configuration and training
  distribution. It is not a general impossibility result.
- Without geometry, residual RL learned state-dependent corrections: +17.4 pp over nominal, +13.3 pp over
  nominal + constant.
- No clear effect of the explicit contact-phase label was detected under this task, observation set and
  training budget (−0.2 pp [−0.6, +0.2]). Raw contact and timing observations remain in both policies.

### Supplementary repeatability (closeout; retrospective, not held-out evidence)

The 8 relevant controllers × 2,400 cases × 3 fresh processes × batch sizes 900 and 23 gave 115,200 episodes,
all recorded. combined − geometry 1.5 cm was negative in every run (selected −0.44 to −0.40 pp, final −0.39
to −0.35 pp), and no repeat-averaged interval included 0. The small disadvantage is therefore **stable under
the tested settings**, and only those. combined − (geometry + 10 mm) was −3.1 pp throughout. Processes with
different seeds gave identical outcomes at a given batch size; changing the batch size changed 0–2 of 2,400
terminal reasons per controller.

Limitations: simulation only, privileged state, translation-only perturbations, three training seeds, v2
designed after v1 diagnostics, training range saturated by the stronger geometry, one reward design; the
repeatability check re-uses the v2 suite. See report Section 7.

## Earlier deliveries (historical, unchanged)

| | v1 | v2 |
|---|---|---|
| Source | [`experiment-v1`](https://github.com/ywen0511/CSCI645-Project/tree/experiment-v1) | [`experiment-v2`](https://github.com/ywen0511/CSCI645-Project/tree/experiment-v2), [`v2.0.0`](https://github.com/ywen0511/CSCI645-Project/tree/v2.0.0) |
| Release | [v1.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v1.0.0) | [v2.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v2.0.0) |
| Report | [report/report.md](report/report.md) (erratum E1) | archived v2.0.0 report in the v2.0.0 release |
| Verification | [docs/RELEASE_VERIFICATION.md](docs/RELEASE_VERIFICATION.md) | [docs/v2/RELEASE_VERIFICATION.md](docs/v2/RELEASE_VERIFICATION.md) |

## Documents

- Closeout: [ASSIGNMENT](docs/closeout/ASSIGNMENT.md) (this assignment, verbatim) · [PLAN](docs/closeout/PLAN.md) ·
  [DECISIONS](docs/closeout/DECISIONS.md) · [REPEATABILITY_PLAN](docs/closeout/REPEATABILITY_PLAN.md) ·
  [ERRATA](docs/closeout/ERRATA.md) · [REPRODUCE](docs/closeout/REPRODUCE.md) · [VERIFICATION](docs/closeout/VERIFICATION.md)
- v2: [ASSIGNMENT](docs/v2/ASSIGNMENT.md) · [PLAN](docs/v2/PLAN.md) · [DECISIONS](docs/v2/DECISIONS.md) ·
  [AUDIT](docs/v2/AUDIT.md) · [V1_ERRATA](docs/v2/V1_ERRATA.md) · [PROTOCOL](docs/v2/PROTOCOL.md) ·
  [REPRODUCE (historical)](docs/v2/REPRODUCE.md) · [diagnostics](report/v2/diagnostics.md) · [geometry ablation](report/v2/geometry_ablation.md)
- v1: [PROJECT_SPEC](docs/PROJECT_SPEC.md) · [EXPERIMENTS](docs/EXPERIMENTS.md) · [IMPLEMENTATION](docs/IMPLEMENTATION.md) ·
  [RUNBOOK](docs/RUNBOOK.md) · [DECISIONS](docs/DECISIONS.md) · [SETUP_REMOTE](docs/SETUP_REMOTE.md) · proposal in [proposal/](proposal/)
- Agent working rules: [AGENTS.md](AGENTS.md). Software reuse and AI-assistance disclosure: report, final section.
