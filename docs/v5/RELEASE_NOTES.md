# v5.0.0 — Matched calibration ablation and dynamic in-grasp slip

Fifth study on the two-Franka bar handover (Isaac Lab 3.0 / Isaac Sim 6.2, PhysX, parallel-jaw grippers, bounded XYZ
residual PPO). Two preregistered studies. Study A executed from tag `experiment-v5a` (simulator code = `experiment-v4`);
Study B frozen and executed from tag `experiment-v5b`. This release: tag `v5.0.0` on branch `study/v5-calibration-slip`.
Earlier releases (v1.0.0 to v4.0.2) are unchanged.

## Findings

**Study A** (2 × 2 × 2 training-free factorial: reference × EMA α × alignment bound; 2,400 fresh held-out cases):
- Calibrated − fixed reference at α 0.2, bound 25 mm: +29.5 pp on `mixed_id` (Bonferroni 97.5% CI [+22.5, +36.5]) and
  +93.0 pp on `grasp_15mm` ([+88.5, +96.5]). Both primary contrasts support a calibration-only improvement.
- EMA α had no effect (identical outcomes in every cell); the 25 mm bound added a few points. Second process:
  2,400/2,400 identical outcomes.

**Study B** (physical slip after the calibration window; 7 conditions × 200 paired cases; 15 learned runs):
- A regulated bar-axis force slides the bar in the giver's fingers. Only slides toward the receiver of up to 8 mm were
  reliable in this setup; the condition table was narrowed to that range before the freeze (`docs/v5/SLIP_FEASIBILITY.md`).
- Primary (`slip_mixed_id`, selected checkpoints): history − feed-forward −1.0 pp (97.5% CI [−3.4, +1.3]); history −
  `geometry_best` (continuous tracking geometry) +0.9 pp ([−2.6, +4.6]). Neither superiority claim is established.
- Exploratory: tracking − one-shot calibration +7.0 pp [+3.0, +11.5] on `slip_mixed_ood`; feed-forward − its one-shot
  parent +3.9 pp [+0.9, +7.3] on `slip_mixed_id`; calibrated parent + 4 mm constant 94.5% on `slip_mixed_id`.
- About 6% of held-out slips missed the 1.5 mm tolerance (`invalid_slip`), a failure for every method.
- History final (10M) checkpoints degraded in three of five seeds (0% on `clean` for two); selection avoided them.
- Mechanisms: reversing or removing the history, or replacing the policy by a development-fitted constant, changed no
  outcome on a 60-case subset. Repeatability: 1,400/1,400 for every rerun entry. V4-suite regression: little change.

Compute: 9.33 A100 GPU-hours before public verification (cap 60).

## Contents

- `checkpoints-formal-<profile>.tar.gz`: every checkpoint (step 0, ten 1M-interval candidates, final, latest) of the
  15 formal runs; `checkpoints-pilot.tar.gz`: both pilot rounds; `checkpoints.json`: index (run, profile, seed,
  transitions, roles, source commit, configuration hash, SHA-256, asset, member).
- Raw records: `raw-study-a`, `raw-development` (probe rounds 1–2, development rounds 1–2), `raw-validation`,
  `raw-final`, `raw-extras` (repeatability, V4-suite regression, mechanisms with development fits, resolved matrices).
- `logs.tar.gz` (job, runner and scheduler logs, ledgers), `analysis.tar.gz` (`results/v5`, `configs/v5`, `report/v5`).
- `report.md`/`report.pdf`, `slides.pptx`/`slides.pdf`, `speaker_notes.md`, `videos.tar.gz` + `videos.json`.
- Source archives of `experiment-v5a`, `experiment-v5b` and `v5.0.0`; `release_manifest.json`,
  `archive_inventories.json`, `run_index.json`, `SHA256SUMS`, `REPRODUCE.md`, `VERIFICATION.md`.

AI assistance: all AI assistance was Anthropic Claude via Claude Code; no other AI coding assistant was used.
