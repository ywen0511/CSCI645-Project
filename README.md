# CSCI 645 — Robust bimanual handover

**V5 is complete and publicly released:** release
[**v5.0.0**](https://github.com/ywen0511/CSCI645-Project/releases/tag/v5.0.0) ·
[V5 report](report/v5/report.md) ([PDF](report/v5/report.pdf)) ·
[slides](report/v5/slides.pdf) ([PPTX](report/v5/slides.pptx), [notes](report/v5/speaker_notes.md)) ·
public verification [docs/v5/VERIFICATION.md](docs/v5/VERIFICATION.md) ·
status [V5_STATUS.json](V5_STATUS.json) (complete). V1–V4 remain released and unchanged
(V4 data [v4.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.0), final review
[v4.0.2](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.2)).

**Start here:** [project overview, V1–V5 (PDF, 8 pages)](report/final/overview.pdf) ·
[overview (Markdown)](report/final/overview.md) · [V5 report](report/v5/report.md) ·
[review and corrections](docs/final_review/REVIEW.md) ·
[defense/demo notes](docs/final_review/DEFENSE_NOTES.md).

There is no active assignment. Do not restart training from any historical runbook
(V3_EXECUTION.md, POST_V3_EXECUTION.md, V4_REMAINING.md, V5_EXECUTION.md).

## What this project studies

Two Franka arms with **two-finger parallel-jaw grippers** hand over a rigid bar in
**Isaac Sim using Isaac Lab / PhysX**. A geometric controller coordinates grasping
and release; PPO optionally adds a bounded XYZ residual. Training uses simulator
interaction, without an external demonstration dataset. Commanded orientations are
fixed. No dexterous hand or real-hardware experiment is claimed.

The project evolved from geometric-control and residual-learning tests (V1/V2), through
synthetic observation uncertainty with a known giver grasp (V3), to physically varied,
unknown initial in-grasp translation (V4), to a matched calibration ablation and a
physical in-grasp slip after calibration (V5). Different versions have different suites;
their rates are not one shared leaderboard.

## Main findings, with their limits

- **V5 Study A** (preregistered 2 x 2 x 2 ablation, 2,400 fresh cases): with EMA alpha and
  alignment bound held fixed, the calibrated giver reference minus the fixed transform is
  +29.5 pp on mixed ID (Bonferroni 97.5% CI [+22.5, +36.5]) and +93.0 pp at +15 mm
  ([+88.5, +96.5]). V4's gain is a calibration effect; EMA filtering had no effect.
- **V5 Study B** (physical slip after calibration; feasible only for slides toward the
  receiver of up to 8 mm): on the primary condition, 4-frame history minus feed-forward is
  -1.0 pp (97.5% CI [-3.4, +1.3]) and history minus continuous tracking geometry +0.9 pp
  ([-2.6, +4.6]): neither superiority claim is established. Tracking geometry, a constant
  offset and feed-forward residuals recover most of what the stale calibration loses; about
  6% of held-out slips are mechanism failures for every method; three of five history seeds
  degraded late in training. Memory is not shown to help in this project.

The V4 findings below are unchanged:

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
- Failure modes (derived on CPU from the V4 records): geometry and combined controllers
  almost never drop the bar (37 drops in 103,200 episodes, no premature-release flags);
  their failures are receiver collisions with the bar end, including the history policy's
  palm-side deficit (31.2% collisions vs 0.5% for its calibrated parent).
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
| V5 report, deck, figures | [report/v5](report/v5/), [results/v5/figures](results/v5/figures/) |
| V5 Study A / Study B metrics | [calibration summary](results/v5/calibration/summary.md), [slip summary](results/v5/slip/analysis/summary.md) |
| V5 checkpoints, raw records, videos | [v5.0.0 release](https://github.com/ywen0511/CSCI645-Project/releases/tag/v5.0.0) ([checkpoints.json](https://github.com/ywen0511/CSCI645-Project/releases/download/v5.0.0/checkpoints.json), [videos.json](https://github.com/ywen0511/CSCI645-Project/releases/download/v5.0.0/videos.json)) |
| V5 reproduction, verification, decisions | [REPRODUCE.md](docs/v5/REPRODUCE.md), [VERIFICATION.md](docs/v5/VERIFICATION.md), [DECISIONS.md](docs/v5/DECISIONS.md) |
| V5 status (complete) and historical assignment | [V5_STATUS.json](V5_STATUS.json), [V5_EXECUTION.md](V5_EXECUTION.md) |
| Proposal failure metrics for V4 (CPU, derived) | [results/v5/cpu](results/v5/cpu/) |

V4 has 25 formal training runs, 54 executed final entries x 2,400 cases = 129,600
episodes, and 55 logical entries including an exact baseline alias. Published artifact
verification resolves 424 checkpoint index entries; these are not 424 independent
training runs or necessarily distinct weight files. Prior remote verification includes
fresh downloads, table/figure regeneration, policy replay/reload and checkpoint resume.
Static offsets, one object and simulated sensing limit V4's generalization; V5 Study B adds
one physical slip model; physical transfer was not performed.

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
- [V4 report](report/v4/report.md) and [v4.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.0)–[v4.0.2](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.2) releases.
- Historical contracts: [V3_EXECUTION.md](V3_EXECUTION.md), [POST_V3_EXECUTION.md](POST_V3_EXECUTION.md), [V4_REMAINING.md](V4_REMAINING.md), [V5_EXECUTION.md](V5_EXECUTION.md).

All repository material is English. Preserve published releases, raw evidence and
experiment tags. Use new tags for new delivery; never overwrite published assets.
