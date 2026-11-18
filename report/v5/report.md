---
title: "Calibration and In-Grasp Slip in Bimanual Handover — V5 Study"
subtitle: "A matched calibration ablation (Study A) and a physical dynamic-slip study (Study B) in Isaac Lab 3.0 / Isaac Sim 6.2 (PhysX) — release v5.0.1"
author: "CSCI 645 Robot Manipulation, Fall 2026 · Yan Wen"
date: "November 2026"
---

**Reading guide.** Section 1 places V5 in the V1–V4 sequence. Section 2 is Study A (a preregistered, training-free
ablation). Sections 3–8 are Study B: the slip mechanism and its feasibility, the methods, the frozen protocol, the
held-out results, mechanisms and failure modes. Sections 9–12 give compute, limitations, reproducibility and
references. Development and pilot numbers are labelled as such and are never used for claims. Every measured number
below is generated from raw records by checked-in scripts; `results/v5/number_audit.json` maps each one to its source.

**v5.0.1.** This revision adds two CPU-only items to v5.0.0, with no new simulation: why EMA α had no effect in
Study A (Section 2), and a post hoc check of the Study B primary contrasts that excludes invalid slips (Section 6.1).
No v5.0.0 result changed; the compute total now also counts the public-verification jobs (Section 9).

## Summary

- **Study A — the calibrated giver reference is what fixed V4's grasp uncertainty.** V4's headline changed three
  settings at once (reference, EMA α, alignment bound). With α 0.2 and bound 25 mm held fixed, on 2,400 fresh
  held-out cases, the 0.5 s calibrated reference minus the fixed nominal transform is +29.5 pp on `mixed_id`
  (Bonferroni 97.5% CI [+22.5, +36.5]) and +93.0 pp at +15 mm (`grasp_15mm`, [+88.5, +96.5]). Both lower bounds are
  above zero, so the frozen rule's verdict is **supported** for both contrasts. EMA filtering had exactly zero
  effect, by construction: with the giver reference on, the filtered estimate never reaches the receiver's command
  while the giver holds the bar, so V4's comparison in effect changed two settings, not three (Section 2). The wider
  bound added +3.2 pp [+1.3, +5.3] on `mixed_id`.
- **Study B — a physical slip after calibration is feasible only in a narrow range.** A regulated bar-axis force
  slides the bar in the giver's fingers (no teleporting). Development showed reliable slides only toward the receiver,
  up to 8 mm; the condition table was narrowed to that range before the freeze (logged).
- **Study B primary contrasts: no superiority established.** On `slip_mixed_id` with selected checkpoints, 4-frame
  history − feed-forward = −1.0 pp (97.5% CI [−3.4, +1.3]) and history − `geometry_best` (continuous tracking
  geometry) = +0.9 pp ([−2.6, +4.6]). Both intervals include zero. A post hoc check that drops every case with an
  invalid slip in a primary arm (177/200 cases kept) gives +0.5 pp
  ([−1.4, +2.3]) and +1.4 pp ([−0.8, +4.0]): the same verdict.
- **What does help is modest and needs no memory.** Exploratory: continuous tracking beats the stale one-shot
  calibration by +7.0 pp [+3.0, +11.5] on `slip_mixed_ood`; the feed-forward residual beats
  its one-shot parent by +3.9 pp [+0.9, +7.3] on `slip_mixed_id`; a +4 mm constant offset
  on the parent reaches 94.5%. About 6% of held-out slips are
  invalid (missed the 1.5 mm tolerance) and count as failures for every method, which caps success at about 94–95%.
- **Late training instability again.** Final (10M) history checkpoints degraded in three of five seeds, two of them completely
  (0.0 / 100.0 / 100.0 / 100.0 / 0.0% on `clean`); validation-based selection avoided them.
- **Conclusion.** In this slip model, continuous geometric estimation and simple offsets handle the slip about as well as
  learning; there is still no held-out evidence in this project that memory helps.

## 1. Motivation and earlier studies

The project (CSCI 645, Robot Manipulation) studies a bimanual handover in Isaac Sim through Isaac Lab: a giver
Franka Panda holds an 18 × 3.5 × 3.5 cm bar with a parallel-jaw gripper and a receiver Franka must grasp it and hold
it alone. Controllers combine a nominal trajectory, a training-free geometric coordination module (target alignment,
a shared holding anchor and a contact-gated release) and optionally a bounded XYZ residual learned with PPO
(±2 cm per axis). The proposal asked whether residual learning on top of geometric coordination improves robustness.

- **V1/V2** (v1.0.0, v2.0.0, v2.1.1): geometric coordination did almost all of the work; learned residuals were
  near-constant offsets that a tuned constant matched.
- **V3** (v3.0.0): with a corrupted bar measurement, geometry that locates the bar from the giver's grasp
  (`giver TCP + fixed grasp transform`) succeeded on all held-out cases, as did every selected policy — a ceiling.
- **V4** (v4.0.0–v4.0.2): made the bar's initial position inside the giver's grasp a physical unknown. The fixed
  transform failed beyond about +10 mm; a 0.5 s calibration of the giver reference fixed most of it; history and
  residual PPO gave no established improvement and were fragile outside their training support.

V4 left two open questions, which V5 answers with two separate preregistered studies:

1. **Study A.** V4's fixed → calibrated comparison also changed the EMA weight (1.0 → 0.2) and the alignment
   bound (15 → 25 mm). Which of the three settings carries the gain?
2. **Study B.** A one-shot calibration is correct only if the grasp stays put. When the bar slides in the giver's
   fingers *after* the calibration window, does a learned residual with observation history recover better than
   the same residual without history, and better than the strongest training-free controller that re-estimates the
   offset continuously?

## 2. Study A — matched calibration ablation

**Design.** A 2 × 2 × 2 factorial of training-free geometry controllers: reference (fixed nominal transform or
0.5 s calibrated), EMA α (1.0 or 0.2) and alignment bound (15 or 25 mm). Each of the 8 configurations runs on 2,400
new held-out cases (V4's 12 conditions × 200; split seed 6457301, disjoint from all V1–V4 seeds). The plan
(`configs/v5/calibration/analysis_plan.json`) and every input were frozen in `configs/v5/calibration/FREEZE.json`
before any simulation and executed from tag `experiment-v5a`, whose simulator code equals `experiment-v4`.

**Primary contrasts** (calibrated minus fixed at α 0.2 and bound 25 mm; case-level paired bootstrap, 10,000 draws;
an improvement is supported only if the Bonferroni 97.5% lower bound is above zero):

| Primary | Condition | Calibrated − fixed | 95% CI | 97.5% CI | Verdict |
|---|---|---:|---|---|---|
| A1 | `mixed_id` | +29.5 pp | [+23.5, +36.0] | [+22.5, +36.5] | supported |
| A2 | `grasp_15mm` | +93.0 pp | [+89.0, +96.0] | [+88.5, +96.5] | supported |

**Acceptance gates.** All 10 entries (8 configurations plus 2 repeat-process entries) have 2,400 records with no
infrastructure error and a clean source tree. The two anchors reproduce V4's configuration and controller hashes
exactly (`ema1p0_fixed_a15` = V4 `geometry_fixed`, `ema0p2_cal050_a25` = V4 `geometry_calibrated`).

![Study A factorial](../../results/v5/figures/study_a_factorial.png)

**Success by configuration (%, 200 cases per cell).**

| Configuration | Reference | EMA α | Bound | clean | grasp 10mm | grasp 15mm | mixed id | mixed ood | boundary x minus 7 |
|---|---|---|---|---|---|---|---|---|---|
| `ema1p0_fixed_a15` | fixed | 1.0 | 15 mm | 100.0 | 39.0 | 7.5 | 72.0 | 74.5 | 96.0 |
| `ema1p0_fixed_a25` | fixed | 1.0 | 25 mm | 100.0 | 40.5 | 0.0 | 70.5 | 74.5 | 96.0 |
| `ema1p0_cal050_a15` | calibrated 0.5 s | 1.0 | 15 mm | 100.0 | 85.5 | 74.0 | 92.0 | 89.0 | 96.0 |
| `ema1p0_cal050_a25` | calibrated 0.5 s | 1.0 | 25 mm | 100.0 | 100.0 | 93.0 | 100.0 | 95.5 | 97.5 |
| `ema0p2_fixed_a15` | fixed | 0.2 | 15 mm | 100.0 | 39.0 | 7.5 | 72.0 | 74.5 | 96.0 |
| `ema0p2_fixed_a25` | fixed | 0.2 | 25 mm | 100.0 | 40.5 | 0.0 | 70.5 | 74.5 | 96.0 |
| `ema0p2_cal050_a15` | calibrated 0.5 s | 0.2 | 15 mm | 100.0 | 85.5 | 74.0 | 92.0 | 89.0 | 96.0 |
| `ema0p2_cal050_a25` | calibrated 0.5 s | 0.2 | 25 mm | 100.0 | 100.0 | 93.0 | 100.0 | 95.5 | 97.5 |

**Exploratory main effects** (averaged over the other two factors; 95% CI): reference +24.8 pp [+19.2, +30.5]
on `mixed_id`, +79.8 pp [+75.5, +83.8] on `grasp_15mm`, +17.8 pp [+12.0, +23.5] on `mixed_ood`; EMA α
+0.0 pp [+0.0, +0.0] everywhere (identical terminal outcomes in every cell); bound
+3.2 pp [+1.3, +5.3] on `mixed_id` and +5.8 pp [+2.3, +9.3] on `grasp_15mm`.

**Why EMA α has no effect (added in v5.0.1).** It is a property of the controller, not a finding about filtering.
With the giver reference on (all eight configurations, as in V4's `geometry_fixed` and `geometry_calibrated`), the
controller's bar position is replaced by the giver-kinematic estimate whenever both giver contacts are closed and the
giver has not released, and the 0.5 s calibration averages the unfiltered measurement, not the EMA output
(`src/csci645_handover/tasks/handover_env.py`, `_measure`). The EMA output reaches the controller only while
settling, when the receiver command is pinned to its start pose, and after the giver releases. A field-by-field
comparison of the executed runs confirms this: across 9,600 paired episodes, every record field except run identifiers and configuration hashes is
identical between α 1.0 and α 0.2, including completion times, alignment corrections and observation errors. In the
traced episode of each configuration (`clean`, 115 samples), the controller's estimate differs in
8 settling samples and 41 samples after release, and the
executed receiver command differs in 0 samples (script `scripts/v5_ema_identity.py`, output
`results/v5/calibration/ema_identity/`). V4's fixed → calibrated comparison therefore
changed two effective settings (reference and bound), not three, and the EMA factor in Study A could not have shown
an effect. This was not recognised when Study A was designed (`docs/v5/DECISIONS.md`).

**Failures** (selected rows; `results/v5/calibration/taxonomy/`). The fixed transform fails by prohibited receiver
collisions with the bar end, almost always with the receiver misaligned at grasp:

| Configuration | Condition | Success | Collision | Invalid reset | Misaligned at grasp |
|---|---|---|---|---|---|
| `ema0p2_fixed_a25` | mixed id | 70.5 | 29.5 | 0.0 | 19.5 |
| `ema0p2_fixed_a25` | grasp 15mm | 0.0 | 99.5 | 0.5 | 0.0 |
| `ema0p2_cal050_a25` | mixed id | 100.0 | 0.0 | 0.0 | 0.0 |
| `ema0p2_cal050_a25` | grasp 15mm | 93.0 | 7.0 | 0.0 | 2.5 |

**Repeatability.** A second process (seed 6457502) reran the two matched primary configurations: 2,400/2,400
and 2,400/2,400 identical terminal outcomes.

**Conclusion.** V4's improvement from fixed to calibrated geometry is a calibration effect. EMA filtering cannot
contribute in this controller (see above), and the wider alignment bound contributes a few points.

## 3. Study B — a physical in-grasp slip

**Question.** When the bar slides in the giver's fingers *after* the 0.5 s calibration window has closed and before
the receiver grasps, does a learned residual with observation history recover better than (B1) the same residual
without history and (B2) the strongest training-free controller that re-estimates the offset continuously?

**Mechanism** (`src/csci645_handover/core/slip.py`; opt-in configuration fields, off by default, so every V1–V4
configuration hash is unchanged — tested). During `[onset, onset + 0.25 s)` an external force along the bar axis
acts at the bar's centre of mass. A PID regulator (kp 6000 N/m, kd 60 N s/m, ki 60,000 N/(m s), cap 90 N) makes
the bar's in-grasp displacement follow a minimum-jerk profile to the case's target; it then holds the target for
0.1 s, after which the force is zero. The giver keeps its normal closed squeeze; the bar is held only by finger
friction, and the force has no vertical component, so the grip alone carries the bar's weight. Nothing writes a pose
or velocity to the bar in scored time. The realized slip (in-grasp displacement change from onset to the end of the
hold) and its error are measured from the simulator and recorded per episode. A slip that misses its target by more
than 1.5 mm (x or z) ends the episode as `invalid_slip`, a failure for every method (like an invalid reset in V4).
Onsets are uniform in [0.7, 1.4] s, so every slip has finished by 1.75 s, before the receiver's 2.0 s grasp.

![Slip mechanism](../../results/v5/figures/slip_mechanism.png)

**Feasibility probe (development only; `docs/v5/SLIP_FEASIBILITY.md`).** Round 1 relaxed the giver's squeeze during
the slip; the bar then sagged 1–10 mm vertically and most slips were invalid. Round 2 kept the full squeeze; with
mechanism M6 (above) and slides starting at offset 0, the acceptance bar (≥ 95% of episodes within 1.5 mm) was met
for −2 to +10 mm:

| Slide target | Valid slips | Median error (mm) | Median vertical drift (mm) | Peak force (N) | Probe acceptance (start 0) |
|---|---|---|---|---|---|
| -7 mm | 1/12 | 10.20 | -9.86 | 70 | no |
| -5 mm | 3/12 | 3.42 | -3.37 | 49 | no |
| -2 mm | 12/12 | 1.07 | -0.19 | 35 | yes |
| +2 mm | 12/12 | 1.34 | +0.15 | 35 | yes |
| +5 mm | 12/12 | 0.73 | -0.50 | 39 | yes |
| +10 mm | 12/12 | 0.78 | -0.67 | 43 | yes |
| +15 mm | 9/12 | 1.08 | -1.00 | 51 | no |

Development round 1 then separated the slide from the final position and showed that validity depends on the
*direction* of the slide: slides toward the giver's palm beyond −2.5 mm were never valid (0 of 476 episodes), and
8–10 mm slides toward the receiver reached only 93.7%. **The accepted slip is therefore a slide toward the receiver of
0 to +8 mm**, with start offset plus slide inside V4's static feasible range [−7, +15] mm. At accepted targets the
mechanism caused no receiver contact before the grasp and no drop; the negative controls (no receiver, giver keeps
holding, table support) produced no success; and a no-slip case with the mechanism enabled was bitwise identical to
the mechanism disabled. Probe and development used about 0.5 GPU-hours (cap 6).

**Condition table, adjusted only to the feasible range before the freeze.** `slip_pos_10` became `slip_pos_8`;
`slip_neg_5` was dropped (no slide toward the palm is feasible); `slip_after_offset` starts at −5 mm and slides +8 mm;
the mixed conditions draw slides uniformly from [0, +8] mm with onset uniform in [0.7, 1.4] s. `slip_mixed_ood` is
therefore out of distribution only in its start offsets and sensor corruption. Study B has seven final conditions:
`clean`, `static_mixed_id`, `slip_pos_5`, `slip_pos_8`, `slip_after_offset`, `slip_mixed_id` (primary) and
`slip_mixed_ood`, 200 paired base cases each.

## 4. Study B methods

All methods receive the same deployable signals as in V4 (corrupted bar translation, proprioception, measured
orientation, finger contacts, phase). None reads the true offset, the true slip or the case label.

| ID | Description |
|---|---|
| `nominal` | scripted trajectory |
| `geometry_fixed` | V4 fixed nominal grasp transform, bound 15 mm |
| `geometry_ema` | V4 EMA geometry (α 0.2) without a giver reference |
| `geometry_calibrated` | V4 one-shot 0.5 s calibration, α 0.2, bound 25 mm — the **parent** of every learned residual |
| `geometry_tracking` | **new**: after the 0.5 s window, the giver-frame correction (measurement − kinematic estimate) keeps being re-estimated by an EMA on every fresh frame while the giver holds the bar |
| `best_constant_geometry` | calibrated parent plus a constant offset, tuned on development |
| `geometry_best` | the strongest training-free controller on development = `tracking_a005_b25` |
| `slip_robust_ff` | PPO residual (±2 cm XYZ) on the parent, current frame only |
| `slip_robust_history` | same, 4-frame stacked history |
| `slip_robust_repeat` | same, current frame repeated 4 times (input-size control) |

**Development tuning** (192 then 168 development cases; V4 ranking on the four validation conditions: success, then
unsafe events, then correction magnitude, then completion time). Six tracking settings and four constant offsets were
tried. `geometry_tracking` = `tracking_a005_b25` (EMA weight 0.05, bound 25 mm), best constant =
`calibrated_const_x+4` (+4 mm along the bar). Five candidates tied on success and unsafe events; V4 never
ranked tracking against constant offsets, so the cross-family tie-break used the common total correction (the
smallest wins), which selected tracking as `geometry_best` (logged before the freeze):

| Candidate (development) | Strata success | Unsafe | Family magnitude (mm) | Total correction (mm) | clean | slip mixed id | slip pos 8 | static mixed id |
|---|---|---|---|---|---|---|---|---|
| `calibrated_const_x+4` | 99.0 | 0.0 | 4.0 | 11.5 | 100.0 | 95.8 | 100.0 | 100.0 |
| `tracking_a005_b25` | 99.0 | 0.0 | 9.8 | 9.8 | 100.0 | 95.8 | 100.0 | 100.0 |
| `tracking_a010_b25` | 99.0 | 0.0 | 9.8 | 9.8 | 100.0 | 95.8 | 100.0 | 100.0 |
| `tracking_a020_b25` | 99.0 | 0.0 | 9.9 | 9.9 | 100.0 | 95.8 | 100.0 | 100.0 |
| `geometry_ema` | 99.0 | 0.0 | 10.2 | 10.2 | 100.0 | 95.8 | 100.0 | 100.0 |
| `tracking_a020_b35` | 99.0 | 0.0 | 10.2 | 10.2 | 100.0 | 95.8 | 100.0 | 100.0 |
| `calibrated_const_x+2` | 97.9 | 1.0 | 2.0 | 10.5 | 100.0 | 91.7 | 100.0 | 100.0 |
| `tracking_a040_b25` | 96.9 | 0.0 | 10.3 | 10.3 | 100.0 | 91.7 | 100.0 | 95.8 |
| `tracking_a040_b35` | 96.9 | 0.0 | 10.7 | 10.7 | 100.0 | 91.7 | 100.0 | 95.8 |
| `geometry_calibrated` | 96.9 | 2.1 | 10.0 | 10.0 | 100.0 | 87.5 | 100.0 | 100.0 |
| `calibrated_const_x-2` | 70.8 | 28.1 | 2.0 | 12.4 | 100.0 | 83.3 | 0.0 | 100.0 |
| `geometry_fixed` | 70.8 | 29.2 | 10.1 | 10.1 | 100.0 | 62.5 | 62.5 | 58.3 |
| `calibrated_const_x-4` | 63.5 | 37.5 | 4.0 | 13.2 | 100.0 | 66.7 | 0.0 | 87.5 |
| `nominal` | 56.2 | 41.7 | 0.0 | 0.0 | 100.0 | 45.8 | 37.5 | 41.7 |

**Training.** V4 robust profile (grasp offsets, sensor corruption) plus a slip with probability 0.5, slide uniform
in [0, +8] mm; V4 PPO settings and curriculum; 10,027,008 transitions per run; seeds 111/222/333/444/555; 15 formal
runs. Pilots (seed 901, about 2 M transitions per profile, never used for claims) showed moving learning curves:
training-episode success from 95.9% to 97.6% (feed-forward),
87.9% to 96.7% (history) and
95.3% to 97.7% (repeat).

![Learning curves](../../results/v5/figures/learning_curves.png)

## 5. Study B protocol and freeze

Seeds: development 6458101, validation 6458201, final 6458301, analysis 6458401, evaluation process 6458501,
repeatability 6458601. Before any final evaluation, `configs/v5/slip/FREEZE.json` fixed 68 inputs — suites (validation
160, final 1,400, mechanism subset 60, the V4 final suite with zero slip 2,400), training protocols, the baseline
selection, the analysis plan (`configs/v5/slip/analysis_plan.json`), matrices and runner manifests, the generator of
the post-selection matrices, the analysis script (unit-tested on synthetic records only) and the simulator source —
at tag `experiment-v5b`. Every formal job ran from a clean clone of that tag.

- **Checkpoint selection.** Ten candidates per run (the first checkpoint at or after each 1 M transitions; step 0 is
  never eligible), ranked by V4's key on the 160 validation cases (`clean`, `static_mixed_id`, `slip_pos_8`,
  `slip_mixed_id`): success, then unsafe rate, then residual magnitude, then later transitions. Invalid resets and
  invalid slips count as failures.
- **Primary** (selected checkpoints, `slip_mixed_id`): **B1** history − feed-forward and **B2** history −
  `geometry_best`. Paired training-seed × base-case bootstrap (10,000 draws, seed 6458401), 95% and Bonferroni 97.5%
  intervals. Superiority only if the 97.5% lower bound is above zero; no equivalence claims.
- **Secondary, exploratory:** all conditions; repeat − feed-forward; tracking − one-shot calibrated; final versus
  selected checkpoints; regression on the V4 final suite; mechanisms on a 60-case subset; repeatability in a second
  process.

![Validation curves](../../results/v5/figures/validation_curves.png)

**Selected checkpoints.**

| Run | Selected checkpoint (transitions) | Validation success (%) |
|---|---|---|
| `slip_robust_ff_s111` | 5,013,504 | 96.2 |
| `slip_robust_ff_s222` | 7,012,352 | 96.2 |
| `slip_robust_ff_s333` | 10,027,008 | 96.2 |
| `slip_robust_ff_s444` | 8,028,160 | 96.2 |
| `slip_robust_ff_s555` | 9,011,200 | 96.2 |
| `slip_robust_history_s111` | 5,013,504 | 96.2 |
| `slip_robust_history_s222` | 9,011,200 | 96.2 |
| `slip_robust_history_s333` | 4,030,464 | 95.6 |
| `slip_robust_history_s444` | 5,013,504 | 96.2 |
| `slip_robust_history_s555` | 5,013,504 | 95.6 |
| `slip_robust_repeat_s111` | 10,027,008 | 96.2 |
| `slip_robust_repeat_s222` | 7,012,352 | 96.2 |
| `slip_robust_repeat_s333` | 10,027,008 | 96.2 |
| `slip_robust_repeat_s444` | 9,011,200 | 96.2 |
| `slip_robust_repeat_s555` | 10,027,008 | 96.2 |

One deviation after the freeze, logged in `docs/v5/DECISIONS.md`: the first submission of the post-selection
evaluations failed before any simulation, because the frozen generator addressed post-selection matrices relative
to the execution checkout. A separate step (`scripts/v5_manifest_paths.py`) re-addressed them through the delivery
checkout, the V4 convention; no frozen input changed.

## 6. Study B held-out results (final suite: 7 conditions × 200 paired base cases)

### 6.1 Primary contrasts

Selected checkpoints, `slip_mixed_id`, paired training-seed × base-case bootstrap (10,000 draws, seed 6458401):

| Primary | Contrast | Difference | 95% CI | Bonferroni 97.5% CI | Superiority |
|---|---|---:|---|---|---|
| B1 | history − feed-forward | −1.0 pp | [−3.1, +0.9] | [−3.4, +1.3] | not established |
| B2 | history − `geometry_best` (tracking) | +0.9 pp | [−2.2, +4.1] | [−2.6, +4.6] | not established |

Both 97.5% intervals include zero. Under the frozen rule, **neither superiority claim is established**: a 4-frame
history does not measurably beat the same residual without history, nor the training-free tracking controller, on
the primary condition. No equivalence is claimed.

**Post hoc sensitivity: excluding invalid slips** (added in v5.0.1; not preregistered). About 5–7% of `slip_mixed_id` episodes end as `invalid_slip` (Section 8). Keeping only
the base cases on which no episode of any primary arm had an invalid slip (177/200), with the same
bootstrap, B1 is +0.5 pp (97.5% CI [−1.4, +2.3]) and B2 is
+1.4 pp ([−0.8, +4.0]). Both intervals still include zero, so the verdict
does not depend on invalid slips. On the exploratory `slip_mixed_ood` (181/200 kept), history −
`geometry_best` becomes +6.1 pp (95% CI [+1.4, +10.7]), against
+3.9 pp [−0.9, +8.7] on all cases. That is one post hoc look at a secondary condition, with a filter that
conditions on episode outcomes, so it is a hypothesis for future work, not a finding (script
`scripts/v5_slip_sensitivity.py`, output `results/v5/slip/sensitivity/`).

![Study B contrasts](../../results/v5/figures/study_b_contrasts.png)

### 6.2 All conditions

Success (%) per method and condition. Learned rows pool five seeds (1,000 episodes per cell); training-free rows are
one deterministic controller (200 episodes per cell). `geometry_best` is the same controller as `geometry_tracking`.

| Method | clean | static mixed id | slip pos 5 | slip pos 8 | slip after offset | slip mixed id | slip mixed ood |
|---|---|---|---|---|---|---|---|
| nominal | 100.0 | 52.5 | 60.0 | 52.0 | 62.0 | 46.0 | 48.5 |
| fixed-transform geometry | 100.0 | 69.0 | 94.0 | 77.0 | 98.5 | 52.5 | 59.5 |
| EMA geometry | 100.0 | 100.0 | 100.0 | 95.5 | 97.5 | 92.0 | 85.5 |
| one-shot calibrated geometry (parent) | 100.0 | 100.0 | 100.0 | 97.5 | 99.5 | 90.0 | 80.5 |
| calibrated + constant | 100.0 | 100.0 | 100.0 | 97.5 | 99.0 | 94.5 | 92.5 |
| tracking geometry (= geometry_best) | 100.0 | 100.0 | 100.0 | 96.5 | 99.5 | 92.0 | 87.5 |
| learned feed-forward (selected) | 100.0 | 99.9 | 100.0 | 96.8 | 98.9 | 93.9 | 90.7 |
| learned 4-frame history (selected) | 100.0 | 99.0 | 100.0 | 96.9 | 99.4 | 92.9 | 91.4 |
| learned repeated current frame (selected) | 100.0 | 100.0 | 100.0 | 97.0 | 98.9 | 94.2 | 88.9 |
| learned feed-forward (final) | 100.0 | 100.0 | 100.0 | 97.0 | 98.8 | 93.8 | 90.9 |
| learned 4-frame history (final) | 60.0 | 63.0 | 80.5 | 78.0 | 79.2 | 63.7 | 59.1 |
| learned repeated current frame (final) | 100.0 | 100.0 | 100.0 | 96.8 | 99.0 | 93.6 | 88.8 |

![Study B by condition](../../results/v5/figures/study_b_conditions.png)

- **The stale calibration is a real but small failure mode.** The one-shot calibrated parent reaches
  90.0% on `slip_mixed_id` and 80.5%
  on `slip_mixed_ood`, versus 100.0% without slip (`static_mixed_id`). Continuous
  tracking minus the one-shot parent (exploratory) is +2.0 pp [−2.0, +6.0] on `slip_mixed_id` and
  +7.0 pp [+3.0, +11.5] on `slip_mixed_ood`.
- **Learned residuals beat their own one-shot parent, without history.** Exploratory, selected checkpoints:
  feed-forward − parent = +3.9 pp [+0.9, +7.3] on `slip_mixed_id` and
  +10.2 pp [+5.9, +15.0] on `slip_mixed_ood`; history − parent =
  +2.9 pp [−0.8, +6.8] and +10.9 pp [+5.4, +16.5]. The
  input-size control (repeat − feed-forward) is +0.3 pp [−1.5, +2.0] on `slip_mixed_id`.
- **A constant offset is as good as anything.** The calibrated parent plus a +4 mm constant along the bar reaches
  94.5% on `slip_mixed_id` and 92.5%
  on `slip_mixed_ood`: every one of its `slip_mixed_id` failures is an invalid slip (Section 8). Slides go only toward
  the receiver, so a constant bias in that direction partly pre-compensates them (a post hoc reading).
- **Invalid slips bound every method.** About 5–7% of the scheduled `slip_mixed_id` slips missed the 1.5 mm
  tolerance (Section 8); they count as failures for every method, so no method can exceed about 94–95% there.

### 6.3 Final checkpoints and per-seed results

Selected and final (10,027,008-transition) checkpoints are reported separately. Feed-forward and repeat final
checkpoints are close to their selected ones. **History final checkpoints degraded in three of five seeds, and two collapsed completely**:
per-seed success on `clean` is 0.0 / 100.0 / 100.0 / 100.0 / 0.0% and on `slip_mixed_id`
47.0 / 92.5 / 76.5 / 92.0 / 10.5% (selected: 93.5 / 94.0 / 92.5 / 92.0 / 92.5%).
Final − selected for history on `slip_mixed_id` is −29.2 pp [−57.9, −3.9].
Validation-based selection avoided the late damage, as in V3 and V4; without it, history would be clearly worse.

## 7. Mechanisms (60-case subset of `slip_mixed_id`; selected history checkpoints)

For each selected history run, the policy was re-evaluated with its 4-frame history reversed, with the current frame
repeated four times, and replaced by a constant residual fitted on its own development records; the zero-residual
parent ran once. Successes out of 60 (agreement of terminal outcomes with the unmodified policy in parentheses):

| Selected history run | Selected | History reversed | Current frame repeated | Development-fitted constant |
|---|---|---|---|---|
| `slip_robust_history_s111` | 52/60 (60) | 52/60 (60) | 52/60 (60) | 52/60 (60) |
| `slip_robust_history_s222` | 52/60 (60) | 52/60 (60) | 52/60 (60) | 52/60 (60) |
| `slip_robust_history_s333` | 52/60 (60) | 52/60 (60) | 52/60 (60) | 52/60 (60) |
| `slip_robust_history_s444` | 52/60 (60) | 52/60 (60) | 52/60 (60) | 52/60 (60) |
| `slip_robust_history_s555` | 52/60 (60) | 52/60 (60) | 52/60 (60) | 52/60 (60) |

The zero-residual parent: 48/60. Every intervention reproduced the unmodified policy's terminal outcome on all 60 cases for all five seeds, although the records confirm that each intervention ran (different configuration hashes and residual means). All failures in these rows are the same eight invalid slips. On this subset, the learned residuals' gain over the parent is fully reproduced by a constant fitted on development records, and the order or presence of past frames does not matter: there is no evidence that the history policies use memory.

## 8. Failures, repeatability, regression and videos

**Failure taxonomy on `slip_mixed_id`** (% of scheduled episodes; `results/v5/slip/analysis/summary.json`):

| Method | Success | Collision | Drop | Timeout | Invalid reset | Invalid slip | Misaligned at grasp | Receiver contact before grasp (episodes) |
|---|---|---|---|---|---|---|---|---|
| nominal | 46.0 | 43.0 | 3.5 | 0.5 | 0.0 | 7.0 | 47.0 | 1 |
| fixed-transform geometry | 52.5 | 40.5 | 0.0 | 0.0 | 0.0 | 7.0 | 16.5 | 0 |
| EMA geometry | 92.0 | 1.5 | 0.0 | 0.0 | 0.0 | 6.5 | 1.0 | 0 |
| one-shot calibrated geometry (parent) | 90.0 | 4.5 | 0.0 | 0.0 | 0.0 | 5.5 | 0.5 | 0 |
| calibrated + constant | 94.5 | 0.0 | 0.0 | 0.0 | 0.0 | 5.5 | 4.5 | 0 |
| tracking geometry (= geometry_best) | 92.0 | 1.5 | 0.0 | 0.0 | 0.0 | 6.5 | 1.0 | 0 |
| learned feed-forward | 93.9 | 0.7 | 0.0 | 0.0 | 0.0 | 5.4 | 0.4 | 0 |
| learned 4-frame history | 92.9 | 0.3 | 0.0 | 0.0 | 0.0 | 6.8 | 65.6 | 3 |
| learned repeated current frame | 94.2 | 0.0 | 0.0 | 0.0 | 0.0 | 5.8 | 0.1 | 0 |

Nominal and fixed-transform geometry fail by prohibited collisions with the bar end, as in V4. For the calibrated,
tracking, constant and learned controllers almost every remaining failure is an `invalid_slip`: the realized slide
missed its target by more than 1.5 mm. These are mechanism failures, decided before the receiver grasps, and they
count against every method. The held-out invalid-slip rate on `slip_mixed_id` (5–7%) is higher than in development
(one in 96 strata cases per controller). The counts differ slightly between methods (11–14 of 200 for the
training-free controllers, 54–68 of 1,000 for the learned ones). This is not explained by receiver contact before the
grasp, which occurred in at most 3 of 1,000 episodes. It depends on the batch layout of the shared PhysX scene: in the
pre-release verification rehearsal (`docs/v5/VERIFICATION.md`), replaying 60 `slip_mixed_id` cases at batch 20 instead
of 240 changed slip validity in 9 of 120 episodes (two controllers), and these were the only outcome differences.

The `misaligned at grasp` flag (receiver more than 10 mm from the nominal grasp point at the nominal grasp time) is high for the history policies although they rarely fail. Their residuals are larger (for seed 333 the median per-episode mean residual is about 4, 7 and −7 mm in x, y and z on `clean`, versus at most 2 mm for feed-forward), so the receiver grasps the 18 cm bar at a different point; the flag records that offset, not a failure.

**Repeatability** (second process, seed 6458601; all training-free baselines and one seed of each learned profile):

| Entry | Matching terminal outcomes |
|---|---|
| `nominal` | 1,400/1,400 |
| `geometry_fixed` | 1,400/1,400 |
| `geometry_ema` | 1,400/1,400 |
| `geometry_calibrated` | 1,400/1,400 |
| `geometry_tracking` | 1,400/1,400 |
| `best_constant_geometry` | 1,400/1,400 |
| `slip_robust_ff_s111__selected` | 1,400/1,400 |
| `slip_robust_history_s111__selected` | 1,400/1,400 |
| `slip_robust_repeat_s111__selected` | 1,400/1,400 |

**Regression on the V4 final suite** (exploratory; 2,400 cases, 12 V4 conditions, zero slip; selected checkpoints of
the slip-trained policies, compared with the published V4 policies of the same architecture):

| Policy (selected) | clean | grasp 2mm | grasp 5mm | grasp 10mm | grasp 15mm | bias 5mm | noise 2mm | delay 2step | mixed id | mixed ood | boundary x minus 7 | boundary z 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| learned feed-forward (V5, slip-trained) | 100.0 | 100.0 | 100.0 | 100.0 | 96.6 | 100.0 | 100.0 | 100.0 | 99.7 | 98.0 | 95.3 | 100.0 |
| V4 feed-forward (V4 published) | 100.0 | 100.0 | 100.0 | 100.0 | 96.5 | 100.0 | 100.0 | 100.0 | 99.4 | 94.5 | 88.2 | 100.0 |
| learned 4-frame history (V5, slip-trained) | 100.0 | 99.9 | 97.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.8 | 97.4 | 81.9 | 99.2 |
| V4 4-frame history (V4 published) | 100.0 | 100.0 | 98.5 | 100.0 | 99.1 | 100.0 | 100.0 | 100.0 | 100.0 | 97.0 | 65.2 | 98.8 |
| learned repeated current frame (V5, slip-trained) | 100.0 | 100.0 | 100.0 | 100.0 | 96.9 | 100.0 | 100.0 | 100.0 | 99.8 | 97.1 | 94.8 | 100.0 |
| V4 repeated current frame (V4 published) | 100.0 | 100.0 | 99.8 | 100.0 | 96.2 | 100.0 | 100.0 | 100.0 | 99.5 | 91.3 | 91.2 | 100.0 |

Training with slip changed performance on the V4 conditions little: most cells are within about 1.5 pp of the V4 policies (history is 1.5 pp lower on `grasp_5mm`), and the slip-trained policies are higher on the harder conditions, notably at the palm-side boundary `boundary_x_minus_7` (outside both training ranges), where V4's history policies were weakest. These are exploratory comparisons across two separately trained policy sets.

**Videos** (`results/v5/videos/videos.json`; chosen by the rule frozen in `configs/v5/video_rule.json` before any
final evaluation): Study A matched fixed vs calibrated on a +15 mm case; Study B one-shot calibrated vs tracking vs
history (and feed-forward) on the first `slip_mixed_id` case the one-shot parent failed; a history failure; a no-slip
control; tracking on a +8 mm slip; and a montage. All nine replays reproduced the evaluation's terminal outcome (`replay_disagreements` is empty); one completion time differs by one control step (feed-forward clip: 4.70 s in evaluation, 4.75 s in the single-environment replay). On the comparison case the one-shot parent and the tracking controller both collide with the slid bar while the history and feed-forward policies succeed; this is one case chosen by the frozen rule, not evidence of a rate. The montage is 44 s.

## 9. Compute

Every job requested one A100-SXM4-80GB GPU; GPU-hours are LSF run times (including simulator start-up), with failed
and killed jobs counted (`results/v5/compute.json`, `scripts/v5_compute.py`). Total: **9.49 GPU-hours** of
the 60 GPU-hour cap.

| Stage | Jobs | GPU-hours | Failed/killed jobs |
|---|---|---|---|
| b development | 2 | 0.15 | 0 |
| b feasibility probe | 2 | 0.15 | 0 |
| b final evaluation | 9 | 0.96 | 4 |
| b formal training | 15 | 5.31 | 0 |
| b mechanisms | 6 | 0.27 | 3 |
| b pilots | 6 | 0.50 | 0 |
| b repeatability | 3 | 0.22 | 1 |
| b v4 regression | 8 | 0.62 | 4 |
| b validation | 15 | 0.75 | 0 |
| study a | 2 | 0.33 | 0 |
| verification | 2 | 0.16 | 0 |
| videos | 1 | 0.05 | 0 |

## 10. Limitations

- **One slip model.** The slip is a regulated bar-axis force on a 0.15 kg bar held by friction, with slides of 0 to
  +8 mm toward the receiver. Slides toward the giver's palm and longer slides were not physically reliable in this
  setup and are not tested. Rotational slip, multiple slips, slip during the receiver's grasp, other objects and
  friction values are out of scope.
- **An inert factor in Study A.** EMA α cannot change the receiver's command when the giver reference is on
  (Section 2), so its main effect is zero by construction; varying it was informative only where the filtered
  measurement is used. The reference and bound results are unaffected.
- **Near-ceiling baselines.** The tracking and constant-offset baselines already succeed on most slip cases, which
  limits how large any learned improvement could be on these suites.
- **Simulation only.** No hardware, vision or dexterous hands; sensing is synthetic (V4 corruption model).
- **Selection noise.** Validation used 160 cases per checkpoint; several candidates tied, and ties were broken by
  the frozen key, not by held-out evidence.
- **Batch layout.** PhysX trajectories can depend on batch layout; repeatability is measured with the same batch
  size, and replays in a single environment (videos, public verification) may differ on a few cases. Every mismatch
  is listed.

## 11. Reproducibility and artifacts

- **Source:** branch `study/v5-calibration-slip`; tags `experiment-v5a` (Study A execution), `experiment-v5b`
  (Study B freeze and execution) and `v5.0.0` (delivery).
- **Release v5.0.0:** every checkpoint of every formal, pilot and probe run with `checkpoints.json`; raw records for
  probe, development, validation, final, mechanisms, repeatability, regression and Study A; traces; logs; report,
  slides, videos; source archives; `SHA256SUMS`, `release_manifest.json`, `REPRODUCE.md`, `VERIFICATION.md`.
- **Regeneration:** `scripts/v5_regen.py` rebuilds every Study A and Study B table and figure from the downloaded raw
  records and compares them with the committed files; `docs/v5/REPRODUCE.md` lists the commands and expected output.
- **v5.0.1 additions (CPU only):** `scripts/v5_ema_identity.py --archive raw-study-a.tar.gz` and
  `scripts/v5_slip_sensitivity.py --runs <extracted raw-final.tar.gz>`; outputs under `results/v5/calibration/ema_identity/`
  and `results/v5/slip/sensitivity/`.
- **Decision log:** `docs/v5/DECISIONS.md` (append-only, UTC times).

## 12. Related work

Learned bimanual handover has been studied mainly with dexterous hands and learned perception [1]; residual learning
also transfers bimanual dexterous skills [2]. Residual reinforcement learning adds a learned correction to a
hand-designed controller [3, 4]. Here the grippers are parallel-jaw and the question is geometric. The simulator is
Isaac Lab on Isaac Sim (PhysX) [5]; PPO [7] is from RSL-RL [6]. Earlier stages of this project are documented in their
own releases [8].

## References

[1] D. Frau-Alfaro, J. Castaño-Amorós, S. Puente, P. Gil, R. Calandra. "Learning Dexterous Object Handover."
IEEE RO-MAN 2025. arXiv:2506.16822.

[2] K. Li, P. Li, T. Liu, Y. Li, S. Huang. "ManipTrans: Efficient Dexterous Bimanual Manipulation Transfer via
Residual Learning." CVPR 2025.

[3] T. Johannink, S. Bahl, A. Nair, J. Luo, A. Kumar, M. Loskyll, J. A. Ojea, E. Solowjow, S. Levine.
"Residual Reinforcement Learning for Robot Control." IEEE ICRA 2019. arXiv:1812.03201.

[4] T. Silver, K. Allen, J. Tenenbaum, L. Kaelbling. "Residual Policy Learning." arXiv:1812.06298, 2018.

[5] M. Mittal et al. "Isaac Lab: A GPU-Accelerated Simulation Framework for Multi-Modal Robot Learning."
arXiv:2511.04831, 2025. Software: Isaac Lab v3.0.0.

[6] C. Schwarke, M. Mittal, N. Rudin, D. Hoeller, M. Hutter. "RSL-RL: A Learning Library for Robotics Research."
arXiv:2509.10771, 2025. Software: rsl-rl-lib 5.5.1.

[7] J. Schulman, F. Wolski, P. Dhariwal, A. Radford, O. Klimov. "Proximal Policy Optimization Algorithms."
arXiv:1707.06347, 2017.

[8] CSCI645-Project releases v1.0.0–v4.0.2, https://github.com/ywen0511/CSCI645-Project/releases.

## Software and AI-assistance disclosure

**Software.** NVIDIA Isaac Sim 6.2.0.0 (PhysX), Isaac Lab v3.0.0, RSL-RL 5.5.1 (PPO), PyTorch 2.11, NumPy,
Matplotlib, imageio/FFmpeg, python-pptx. No external datasets or demonstrations; all training data are simulator
transitions.

**AI assistance.** All AI assistance was Anthropic Claude via Claude Code; no other AI coding assistant was used.
The V5 implementation, probes, experiments, analysis code, figures, this report, the slides and the videos were
produced by Claude Code working from `V5_EXECUTION.md` on the owner's behalf, on the owner's account and compute.
Decisions are logged with UTC times in `docs/v5/DECISIONS.md`; every measured number comes from checked-in scripts
applied to the released raw records (`results/v5/number_audit.json`). The v5.0.1 additions were made by Claude Code
on CPU from the v5.0.0 raw records.
