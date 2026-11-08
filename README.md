# CSCI 645 — V3 observation robustness in bimanual handover

**Remote execution agent: [read and execute V3_EXECUTION.md](V3_EXECUTION.md).**
It is the complete assignment: validate the prepared implementation on the remote
GPU, freeze the protocol, train/evaluate all required methods, analyze the findings,
create the report/slides/videos, publish every result and saved checkpoint in a
new GitHub Release, and verify a fresh download. No local files or prior chat are
needed. Do not stop at a plan, CPU tests, or launching training.

**Current status: CPU preparation complete; remote simulation/training is NOT done.**
No GPU or simulator workload was run during preparation. See
[preparation evidence](docs/v3/PREPARATION.md) and [V3 status](V3_STATUS.json).
The prepared simulator integration requires the remote acceptance checks before
formal experiments. New scientific results must not be inferred from CPU tests.

This extends the existing Isaac Sim + Isaac Lab two-Franka, two-finger-gripper
handover project. V3 asks when geometric coordination and bounded PPO residuals
remain effective with translation-estimation bias, noise and delay, and whether
short history helps beyond filtering, a giver-grasp kinematic baseline, and a
matched-input-size control. Existing v1/v2 results are preserved.

| Component | Prepared here | Remote work |
|---|---|---|
| Sensors/controllers | Corruption, EMA, giver reference, history, intervention hooks, CPU tests | Simulator timing/contact/zero-residual acceptance and any fixes |
| Experiment design | Split generator, development/validation cases, five training profiles, baseline matrices | Development baselines/pilots, freeze, final suite, 23 training runs |
| Evaluation/analysis | Provenance checks, count reconciliation, paired clustered bootstrap | Full matrix, checkpoint selection, mechanism and repeatability studies |
| Delivery | Complete assignment and acceptance/publication contract | Report, slides, videos, all raw results/checkpoints, release and fresh verification |

## Start

```bash
git clone --branch study/v3-observation-robustness https://github.com/ywen0511/CSCI645-Project.git
cd CSCI645-Project
cat V3_EXECUTION.md
```

For CPU-only checks in an isolated environment with torch, numpy and pytest:

```bash
CUDA_VISIBLE_DEVICES='' python -m pytest -q
python scripts/v3_prepare.py
```

`v3_prepare.py` creates development inputs, not results. Read the execution document
before installing the simulator or starting any remote job. No external training
dataset is required; data come from simulator interaction.

## Prior completed work

- [V2 final release](https://github.com/ywen0511/CSCI645-Project/releases/tag/v2.1.1)
- [V2 report](report/v2/report.md) and [verification](docs/closeout/VERIFICATION.md)
- [Historical V2 README](README_V2_CLOSEOUT.md); its completion flags and commands
  concern the archived study, not V3.
- [Original proposal](proposal/proposal.txt), preserved as submitted.

V3 work stays on `study/v3-observation-robustness`. The execution agent must publish
an immutable `experiment-v3` tag and a verified `v3.0.0` release (or a new version
if those names are already in use), without rewriting old history or releases.
