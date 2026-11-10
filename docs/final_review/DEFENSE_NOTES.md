# Presentation and defense notes

Use the [six-page overview](../../report/final/overview.pdf) as the current concise
reading artifact and the archived V4 deck for detailed figures. Read
[REVIEW.md](REVIEW.md) before presenting old slides: slides 1, 6 and 14 over-isolate
calibration and describe a stronger continuous failure threshold than the grid supports.
Explain the controller-package comparison verbally or display overview pages 2–3.
The new sensitivity analysis belongs on overview page 4; it is explicitly post hoc.

## Five-minute narrative

1. **0:00–0:40 — Task and hypothesis.** Two Franka arms with parallel-jaw grippers hand
   over a rigid bar. Ask whether a bounded learned correction improves a geometric
   controller. Define success as independent receiver holding, not visual contact.
2. **0:40–1:20 — Why the project evolved.** V1 exposed a step-zero selection issue;
   V2 established stronger controls and a residual-only benefit over nominal control;
   V3 hit a ceiling because the giver reference assumed an exact grasp transform.
3. **1:20–2:10 — V4 design.** Physically vary initial in-grasp translation, share the
   configured information channels, freeze development/validation/final separation,
   use five seeds and a matched repeated-frame control. Distinguish unknown static
   translation from dynamic slip, vision or dexterous manipulation.
4. **2:10–3:00 — Main outcome.** Show overview page 3. The calibrated controller package
   is strong. Its comparison with historical fixed geometry changes EMA and alignment
   bounds too. Both primary learning intervals touch zero: no established superiority.
5. **3:00–3:50 — Failure analysis.** Show page 4. History degrades at the unseen palm-side
   boundary. On the common-valid reset subset the deficit persists. Name the analysis
   as retrospective, keep the primary denominator intact, and show the uncertainty.
6. **3:50–4:30 — Demo.** Show the same grasp-15 case under fixed geometry, calibrated
   geometry and selected history; finish with a calibrated mixed-OOD clip. Explain
   that illustrative videos are not an estimator of aggregate success.
7. **4:30–5:00 — Contribution and limits.** The contribution is a controlled empirical
   study with reproducible artifacts and a scoped result. One object, simulated
   sensing, static offsets and fixed orientations limit generalization. All training
   checkpoints and raw evidence are publicly indexed, including unfavorable results.

## Demo selection (existing videos, no new simulation)

Download [videos.tar.gz](https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/videos.tar.gz).
Use [the clip index](../../results/v4/videos/video_index.json) to locate each basename,
check its SHA-256, and read its outcome and checkpoint. Files may have archive prefixes;
do not assume the archive is flat. Keep the sidecar JSON with each clip.

| Order | Clip basename | What to say |
|---|---|---|
| 1 | `nominal_vs_geometry_vs_learned__geometry_fixed__v4-final-grasp_15mm-0000.mp4` | Receiver collision under the historical fixed configuration. |
| 2 | `nominal_vs_geometry_vs_learned__geometry_calibrated__v4-final-grasp_15mm-0000.mp4` | Same case succeeds with the calibrated configuration; not a calibration-only ablation. |
| 3 | `nominal_vs_geometry_vs_learned__combined_robust_history_s111_selected__v4-final-grasp_15mm-0000.mp4` | A learned policy also succeeds; one clip cannot establish superiority. |
| 4 | `noisy_calibration__geometry_calibrated__v4-final-mixed_ood-0000.mp4` | Illustrates measurement-based calibration with corrupted sensing. |

The 52.9 s `montage.mp4` is a fallback. Do not invent a learned-policy failure video:
the frozen video rule did not yield one on its chosen cases. Show the boundary table
for aggregate learned failures. A nominal success clip also exists; acknowledge it
if comparing the same case, instead of implying nominal always fails.

## Likely questions

**Did the project fail because PPO did not win?** No. It tests a hypothesis against
strong controls. V2 showed improvement over weak nominal control; V4 did not establish
improvement over strong baselines and identified an important failure regime.

**Why Isaac Sim and Isaac Lab?** They implement the chosen physical contact task,
parallel environments and RSL-RL integration. Platform choice does not establish
physical validity; the contact/reset checks and specified versions define the scope.

**Where are the training data?** They are online simulator transitions. The repository
contains configurations and summaries; release assets contain logs, raw evaluation
records and checkpoints. There is no external demonstration dataset to download.

**Is this two hands or two fingers?** Two robot arms, each carrying a two-finger
parallel-jaw gripper. It is not an articulated multi-finger hand.

**Does calibration alone explain the 89-point grasp-15 improvement?** The final
comparison changes reference, EMA and alignment bound. Matched development controls
support a calibration mechanism, but are not held-out causal confirmation.

**Why not say history is useless?** Only the tested architectures, training budgets,
sensor process and subsets are covered. The interventions suggest a constant component
and limited demonstrated temporal-order benefit, not a universal impossibility.

**Do the confidence intervals account for everything?** They resample paired training
seeds and base cases. They do not cover arbitrary simulator versions, hardware,
unseen object distributions or every evaluation-process variation.

**Why keep invalid resets as failures?** That was the frozen denominator and is shared
by every method. The new common-valid sensitivity uses one joint subset, avoids
method-specific removal, and discloses the conditioning limitation.

**Why is a selected checkpoint different from the final one?** Selection uses only
validation, excludes step zero in V4 and can choose an earlier checkpoint. Final
checkpoints expose late instability; both are published.

**Are 424 checkpoints 424 independent models?** No. This is a checkpoint-index entry
count, including named roles and aliases. Formal training has 25 runs.

**What would make the next experiment stronger?** A separately planned matched-bound,
matched-filter calibration ablation on new cases, or a physically validated dynamic-slip
intervention. Neither should be relabeled as part of the already-frozen primary test.

**How much did AI do?** Implementation, experiment orchestration, analysis and writing
were AI-assisted, with local Codex maintenance/review and remote agent execution.
Explain that honestly and be ready to trace the task, evaluator and result files.
