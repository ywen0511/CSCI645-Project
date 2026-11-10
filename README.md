# CSCI 645 — Robust bimanual handover

**The V4 experimental study is complete and publicly released.** This branch adds a
final project synthesis, independent CPU audit and retrospective sensitivity analysis.
The supplement's release/public-download verification is tracked separately in
[FINAL_REVIEW_STATUS.json](FINAL_REVIEW_STATUS.json). No new training is required.

**Start here:** [six-page project overview (PDF)](report/final/overview.pdf) ·
[overview (Markdown)](report/final/overview.md) ·
[review and corrections](docs/final_review/REVIEW.md) ·
[defense/demo notes](docs/final_review/DEFENSE_NOTES.md).

**Execution agent:** read [FINAL_DELIVERY_HANDOFF.md](FINAL_DELIVERY_HANDOFF.md) and
complete its finite publication and public-download checks. That document is the
current assignment and contains commands, authority, deliverables and completion gates.
Do not restart training from the historical V3/V4 execution runbooks.

## What this project studies

Two Franka arms with **two-finger parallel-jaw grippers** hand over a rigid bar in
**Isaac Sim using Isaac Lab / PhysX**. A geometric controller coordinates grasping
and release; PPO optionally adds a bounded XYZ residual. Training uses simulator
interaction, without an external demonstration dataset. Commanded orientations are
fixed. No dexterous hand or real-hardware experiment is claimed.

The project evolved from geometric-control and residual-learning tests (V1/V2), through
synthetic observation uncertainty with a known giver grasp (V3), to physically varied,
unknown initial in-grasp translation (V4). Different versions have different suites;
their rates are not one shared leaderboard.

## Main findings, with their limits

- In V4's grasp-15 condition, historical fixed geometry succeeds in 5.5% of cases and
  calibrated geometry in 94.5%. **This compares controller configurations:** the
  calibration configuration also changes EMA filtering and the alignment bound.
  Matched development controls support a calibration mechanism but are not held-out
  causal confirmation. The discrete x/z grid does not establish an exact x-only threshold.
- Selected robust history reaches 100% on mixed ID, but both prespecified primary
  intervals touch zero: improvement over robust feed-forward or the strongest constant
  baseline is not established. This is not an equivalence result.
- At the unseen palm-side boundary, selected history reaches 65.2% versus calibrated
  geometry's 96.5%. The new **post hoc** common-valid-reset analysis retains a deficit
  of 30.79 pp (95% interval [-43.60, -18.20]); invalid resets alone do not explain it.
- V2 residual-only learning did improve over nominal control. The overall conclusion
  is scoped: the tested learned residuals do not consistently improve strong geometry,
  not that reinforcement learning can never help.

The independent CPU audit reconciles 129,600 final records, both primary bootstrap
comparisons, 78 frozen source hashes and 25 selections from recorded validation
summaries. See [audit.json](results/final_review/audit.json) for exact checks and limits.
CPU checks do not establish contact physics or independently replay policy weights.

## Results and artifact map

| Need | Where |
|---|---|
| Current concise narrative and sensitivity plot | [report/final](report/final/) |
| Full archived V4 report, deck and speaker notes | [report/v4](report/v4/), read with [corrections](docs/final_review/REVIEW.md) |
| All formal/pilot/smoke checkpoints, raw records, logs, videos and original documents | [v4.0.0 data release](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.0) |
| Repaired reproduction tooling | [v4.0.1 tooling release](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.1) |
| Exact inherited download URLs, sizes and hashes | [INHERITED_ASSETS.json](results/final_review/INHERITED_ASSETS.json) |
| Checkpoint identities | [public checkpoints.json](https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/checkpoints.json) |
| Success rates and paired effects | [results/v4/summary](results/v4/summary/) |
| Reproduction and prior remote GPU verification | [REPRODUCE.md](docs/v4/REPRODUCE.md), [VERIFICATION.md](docs/v4/VERIFICATION.md) |
| Frozen scientific protocol / experiment source | [analysis plan](configs/v4/analysis_plan.json), [experiment-v4](https://github.com/ywen0511/CSCI645-Project/tree/experiment-v4) |
| Completed study status | [POST_V3_STATUS.json](POST_V3_STATUS.json) |
| Current remaining publication assignment | [FINAL_DELIVERY_HANDOFF.md](FINAL_DELIVERY_HANDOFF.md) |

V4 has 25 formal training runs, 54 executed final entries x 2,400 cases = 129,600
episodes, and 55 logical entries including an exact baseline alias. Published artifact
verification resolves 424 checkpoint index entries; these are not 424 independent
training runs or necessarily distinct weight files. Prior remote verification includes
fresh downloads, table/figure regeneration, policy replay/reload and checkpoint resume.
Static offsets, one object and simulated sensing limit generalization; dynamic slip
and physical transfer were not performed.

## Reproduce this CPU review

Use Python 3.11+ with NumPy; fetch tags so frozen Git objects are available.
The full study reproduction remains the separate version-pinned V4 runbook above.

```bash
git clone --branch study/v4-grasp-uncertainty https://github.com/ywen0511/CSCI645-Project.git
cd CSCI645-Project
git fetch origin --tags
python3 -m venv .venv-cpu
.venv-cpu/bin/python -m pip install numpy==2.4.6
mkdir -p downloads/v4-review
curl -fL --retry 2 -o downloads/v4-review/raw-final.tar.gz \
  https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/raw-final.tar.gz
CUDA_VISIBLE_DEVICES='' .venv-cpu/bin/python scripts/final_review_audit.py \
  --archive downloads/v4-review/raw-final.tar.gz --out outputs/final-review/audit.json
```

The auditor fails on checksum, provenance, pairing, denominator or primary-estimate
disagreement. It never imports Isaac Lab. The plot and overview builder is
[scripts/final_review_build.py](scripts/final_review_build.py), requiring ReportLab and
Matplotlib; exact setup and test commands are in the current handoff.

## Earlier studies and preserved contracts

- [Original submitted proposal](proposal/proposal.txt), preserved unchanged.
- [V2 report](report/v2/report.md) and [v2.1.1 release](https://github.com/ywen0511/CSCI645-Project/releases/tag/v2.1.1).
- [V3 report](report/v3/report.md), [v3.0.0 release](https://github.com/ywen0511/CSCI645-Project/releases/tag/v3.0.0), and [v3.0.1 maintenance](https://github.com/ywen0511/CSCI645-Project/releases/tag/v3.0.1).
- Historical contracts: [V3_EXECUTION.md](V3_EXECUTION.md), [POST_V3_EXECUTION.md](POST_V3_EXECUTION.md), [V4_REMAINING.md](V4_REMAINING.md).

All repository material is English. Preserve published releases, raw evidence and
experiment tags. Use new tags for new delivery; never overwrite published assets.
