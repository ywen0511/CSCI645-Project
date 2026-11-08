---
title: "Observation Robustness in Bimanual Handover — v3 Study"
subtitle: "Translation-estimation bias, noise and delay against geometric control and residual PPO, with short observation history, filtering and a giver-grasp reference (Isaac Lab 3.0 / Isaac Sim 6.2, PhysX) — release v3.0.0"
author: "CSCI 645 Robot Manipulation, Fall 2026 · Yan Wen"
date: "November 2026"
---

**Reading guide.** Section 1 states the question and why it follows from the earlier studies. Sections 2–4
define the task, the synthetic sensor, the controllers and the protocol. Section 5 reports development
findings (used to choose baselines and freeze the protocol; not held-out evidence). Sections 6–8 report the
new held-out results, mechanisms and repeatability. Section 9 lists limitations. Previous-study numbers are
quoted from the v2 report and labeled as such. Every measured number in this report is generated from the
raw records by checked-in scripts; `results/v3/number_audit.json` maps each one to its source file and field.

## Summary

- **The question.** v2 found that a training-free geometry controller, optionally with a tuned constant offset,
  was as good as or better than residual PPO on top of it when the object position is measured accurately. v3
  asks whether this still holds when the object-translation measurement is corrupted by bias, noise and delay,
  and whether noise-trained residuals or a five-frame observation history help.
- **The strong baseline saturates the held-out suite.** The shared estimator (`geometry_common`: no smoothing,
  plus a kinematic reference from the giver's grasp while the giver holds the bar) succeeds in
  100.0% of `mixed_id` cases and 100.0% of
  `mixed_ood` cases, and in every one of the 13 conditions (2,600 cases). The giver reference removes almost
  all of the translation error before release, which is where the geometry controller uses the estimate.
- **Primary contrasts are exactly zero.** With selected checkpoints on `mixed_id`, robust history − robust
  feed-forward = +0.0 [+0.0, +0.0] pp (95% CI; 97.5% Bonferroni
  interval [+0.0, +0.0]), and robust history −
  `geometry_best_constant` = +0.0 [+0.0, +0.0] pp
  (97.5%: [+0.0, +0.0]). Every selected combined
  policy, clean- or noise-trained, feed-forward, history or repeated-current, succeeded on every case. The
  zero-width intervals are a ceiling effect: this suite cannot rank them, and nothing here shows that history
  or noise-trained residuals help.
- **Without the giver reference, the estimator matters a lot.** Raw-estimate geometry falls to
  0.5% at 2 mm noise and 0.0% on `mixed_id`,
  almost entirely by release-gate timeouts. EMA filtering (α = 0.2) restores noise robustness but not 10 mm
  bias (67.5%), which causes collisions. Delay up to 4 steps (200 ms) has no
  effect in this nearly stationary handover.
- **Learning is fragile late in training; validation selection matters.** Three of five robust-history runs
  degrade by the 10M-transition final checkpoint, and seed 55 collapses (19.2% on
  validation, mostly collisions). Their final checkpoints lose −28.2 [−56.4, −5.4] pp
  against `geometry_common` on `mixed_id` (per seed −35.5 / +0.0 / −22.0 / −2.0 / −81.5).
  The three repeated-current runs and all feed-forward runs stay at ceiling.
- **Residual-only history learning does not beat the nominal script.** Selected residual-only history
  policies: 68.7% on `mixed_id` vs nominal 70.5%
  (difference −1.8 [−10.2, +4.4] pp; per seed
  +0.0 / −17.0 / +6.5 / +1.5 / +0.0). This differs from v2, where residual-only PPO
  improved on the nominal script with accurate state.
- **Learned residuals are near-constant offsets that ignore the sensor error.** Across the combined families,
  the episode-mean x residual has intercepts -2.6 to -0.4 mm, slope on the injected sensor bias
  at most 0.008 in absolute value, and slope on the true object offset at most
  0.079.
- **Repeatability.** On a predeclared 65-case subset, 2,730 of 2,730 reruns (3 process seeds × batch 1 and 23
  × 7 entries) reproduced the original terminal outcome; sensor streams were identical.

## 1. Question, prior studies and hypotheses

**Previous studies (not re-measured here).** v1 showed that a training-free geometry module (alignment of the
receiver to the measured bar position, a shared-holding anchor and a contact-gated release) is decisive for a
two-Franka bar handover. Its checkpoint selector chose the untrained policy in 8 of 9 runs, so v1 could not
say whether residual RL helps. v2 audited v1 and ran a preregistered harder experiment with accurate state.
All-case success was nominal 65.2%, residual 82.6%, geometry 96.5%, combined (geometry + residual PPO) 96.1%,
and geometry plus a tuned constant offset 99.2% (v2 report, release v2.1.1 [7]). Learned residuals on top of
geometry behaved like a small constant bias.

**Why v3.** v2 used accurate object state, one object, three seeds and only initial-pose and release-time
perturbations. Real handovers estimate the object position from imperfect sensing. If geometry relies on that
estimate, measurement errors might expose a weakness that a learned residual, possibly with memory, could
repair. v3 tests the boundary of the v2 finding under controlled translation-measurement errors, keeping
everything else fixed.

**Question.** When strong geometric handover control already works, how do object-translation estimation
errors affect geometry and residual learning, and does a short observation history improve robustness?

**Hypotheses (declared before any held-out result).** (H1) Bias, noise and delay affect the controllers
differently, so severity curves and failure modes are more informative than one pooled number. (H2)
Noise-trained residuals may be more robust than clean-trained ones. (H3) A five-frame history may help under
partial observability, beyond the extra input parameters (tested against a repeated-current-frame control of
identical size). (H4) Filtering and a giver-grasp kinematic reference may remove most of that benefit.

## 2. Task and synthetic sensor

**Scene and control (unchanged from v2).** Isaac Lab v3.0.0 [4] on Isaac Sim 6.2.0.0 with PhysX; two fixed-base
Franka Panda arms with parallel-jaw grippers; one rigid 20 cm bar. Physics runs at 120 Hz, control at 20 Hz
(decimation 6), through differential IK with fixed hand orientations. A giver holds the bar; the receiver
approaches on a scripted schedule; the giver releases through a contact-gated release (1 s cap). Success
requires two continuous seconds in which only the receiver holds the bar: giver fingers open, no giver or
table support, no drop, bounded relative drift. Reset failures are counted separately from task failures.
Per-case physical perturbations are the initial bar offset (uniform, up to ±2 cm per axis) and the release
time (up to ±0.3 s).

**Synthetic translation sensor.** Only the bar's translation measurement is corrupted. Orientation, joint
states, TCP proprioception, gripper widths and contact forces stay accurate. At control step *k* the measured
position is

  y_k = x_{k−d} + b + σ · n(seed, k),  then  ŷ_k = α · y_k + (1 − α) · ŷ_{k−1},

where x is the true position, d the delay in control steps, b a per-episode bias vector, σ the noise standard
deviation, n a standard normal drawn from a counter-based generator indexed by the case's sensor seed and the
step counter (so every controller sees the identical noise sequence for a case), and α the EMA weight
(α = 1: no smoothing). **Giver reference:** while the giver holds the bar, the estimate is the giver TCP
position minus the nominal grasp offset, rotated by the TCP orientation. This is a kinematic inference from
proprioception that does not use the corrupted sensor. After release, the estimate falls back to ŷ. The
sensor is a controlled model of translation-estimation error, **not a vision system and not a sim-to-real
claim**.

**Conditions (final suite, 200 base cases × 13 conditions = 2,600 cases).** Every condition reuses the same
200 base cases (same seeds, physical offsets and release times), so comparisons across conditions and methods
are paired. Conditions: `clean` (no physical or sensor perturbation), `physical_only`, bias 2/5/10 mm per axis,
noise σ = 1/2/4 mm, delay 1/2/4 steps, `mixed_id` (random bias ≤ 5 mm, σ = 2 mm, delay 2: the training
distribution's typical corruption) and `mixed_ood` (bias ≤ 10 mm, σ = 4 mm, delay 4). Validation uses
separate seeds (40 base cases × 6 conditions = 240 cases); development uses another separate set (312 cases).

## 3. Controllers and learned policies

| controller | receiver target | estimator |
|---|---|---|
| nominal | scripted schedule | none (does not use the object estimate) |
| geometry_raw | geometry (alignment ≤ 1.5 cm, anchor, gated release) | raw (α = 1, no giver reference) |
| geometry_filtered | as above | EMA α = 0.2, no giver reference |
| geometry_common | as above | α = 1 + giver reference (the estimator shared by all combined policies) |
| geometry_best_constant | as above + best constant x-offset | same as geometry_common |
| geometry_giver | best giver-reference configuration | same as geometry_common |
| combined_* (learned) | geometry_common + PPO residual `0.02 · tanh(a)` m per axis | same as geometry_common |
| residual_robust_history (learned) | nominal + PPO residual | same sensor, 5-frame history |

Residual policies follow residual RL [2, 3]: a learned correction added to a fixed controller. Object
handover as an RL problem is studied e.g. in [1]; here the handover itself is scripted and only the receiver's
target is corrected. Learned families (PPO [6] from RSL-RL 5.5.1 [5], actor/critic MLP [128, 128], ELU; 10,027,008 transitions each, 1,024
environments × 32 steps per iteration):

- `combined_clean_ff`: trained without sensor corruption, single frame (46 inputs).
- `combined_robust_ff`: trained with the corrupted sensor (25% clean episodes; otherwise bias ≤ 5 mm, σ ≤ 2 mm,
  delay ≤ 2), single frame.
- `combined_robust_history`: same training distribution, five frames, oldest to newest (230 inputs).
- `combined_robust_repeat`: same as history, but all five slots hold the current frame (230 inputs; the memory
  control with identical input size and network width; seeds 11/22/33).
- `residual_robust_history`: residual on the nominal script, five frames.

Seeds 11/22/33/44/55 (23 runs). The actor and critic have 45,575 parameters with 46 inputs and 92,679 with 230.

## 4. Protocol, selection and counts

**Development and freeze.** Remote acceptance (10 of 10 checks passed; Section 5.1) came first, then
development baseline searches and bounded pilots on development cases only, then a protocol freeze (tag
`experiment-v3` = `3811f5da`). All 23 formal runs, validation, final evaluation and the video rule ran from the
clean `experiment-v3` source; every record stores the source commit and a clean-source flag.

**Checkpoint selection (validation split).** Each run saves every ~1M transitions. The candidates are the first
saves at or after 2, 4, 6, 8 and 10M transitions, evaluated on all 240 validation cases. Step 0 (untrained) is
also evaluated as a control and is never eligible. The frozen rule picks the highest validation success, then
the lowest collision rate, then the smallest mean bounded residual, then the latest step. The final checkpoint
(after the last iteration) is evaluated as well, as a declared secondary analysis.

**Final matrix.** Six baselines plus 23 runs × {selected, final}, 2,600 cases each:
135,200 logical episodes, batch 256, one fresh simulator process per entry. Three baseline roles
coincide exactly (`geometry_common` = `geometry_best_constant` = `geometry_giver`; the development search chose
the zero constant and the same giver-reference estimator). They were evaluated once and reused under recorded
aliases, so 130,000 episodes were executed. Aliases are not counted as independent evidence.
All scheduled case IDs were recorded, with 0 invalid resets and no infrastructure errors.

**Uncertainty.** Paired bootstrap (10,000 replicates, seed 6455401) over training seeds and shared base-case
clusters, keeping paired conditions together. 95% intervals; for the two primary contrasts, also 97.5%
Bonferroni intervals. Deterministic baselines are not treated as extra seeds. With five seeds, the intervals
describe these seeds and cases, not universal superiority.

## 5. Development findings (not held-out evidence)

### 5.1 Acceptance

| acceptance check | pass |
|---|---|
| 1. physical pipeline and negative controls | yes |
| 2. zero residual and residual mechanics | yes |
| 3. sensor model and layout pairing | yes |
| 4. reset boundaries and tokens | yes |
| 5. no hidden translation path | yes |
| 6. zero error sensor vs archived path | yes |
| 7. estimators and gate | yes |
| 8. inputs history normalization | yes |
| 9. ppo smoke save reload resume | yes |
| 10. eval cache rejection and resume | yes |

Highlights: a zero residual reproduces its deterministic controller exactly; the sensor layouts used by
feed-forward and history inputs pair to within 6e-8 m; no input path carries the true translation; with zero
sensor error the new code reproduces the archived v2 path episode for episode. The raw (unsmoothed) estimate
blocks the contact-gated release under noise (check 7). That is why the shared estimator was chosen
in development, before any held-out data.

### 5.2 Baseline search (144 development selection cases, six strata)

| role | candidate | EMA alpha | giver ref. | bound [cm] | constant x [mm] | selection success (144 dev cases) |
|---|---|---|---|---|---|---|
| geometry_common | ema1p0_giver1/geom15_x+00 | 1.0 | True | 1.5 | 0.0 | 100.0% |
| geometry_best_constant | ema1p0_giver1/geom15_x+00 | 1.0 | True | 1.5 | 0.0 | 100.0% |
| geometry_raw | ema1p0_giver0/geom15_x+00 | 1.0 | False | 1.5 | 0.0 | 66.7% |
| geometry_filtered | ema0p2_giver0/geom15_x+00 | 0.2 | False | 1.5 | 0.0 | 100.0% |
| geometry_giver | ema1p0_giver1/geom15_x+00 | 1.0 | True | 1.5 | 0.0 | 100.0% |
| nominal | nominal | – | – | – | – | 81.2% |

Development candidates by condition (successes of 24, 1.5 cm bound, zero constant):

| development candidate (1.5 cm, 0 mm) | clean | physical only | bias 2mm | bias 5mm | bias 10mm | noise 1mm | noise 2mm | noise 4mm | delay 1step | delay 2step | delay 4step | mixed id | mixed ood |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nominal | 24 | 18 | 18 | 18 | 19 | 18 | 19 | 18 | 19 | 19 | 19 | 19 | 18 |
| ema1p0_giver0/geom15_x+00 | 24 | 24 | 24 | 24 | 19 | 6 | 0 | 0 | 24 | 24 | 24 | 0 | 0 |
| ema0p5_giver0/geom15_x+00 | 24 | 24 | 24 | 24 | 19 | 24 | 13 | 0 | 24 | 24 | 24 | 13 | 0 |
| ema0p2_giver0/geom15_x+00 | 24 | 24 | 24 | 24 | 19 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 23 |
| ema1p0_giver1/geom15_x+00 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 |
| ema0p5_giver1/geom15_x+00 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 |
| ema0p2_giver1/geom15_x+00 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 | 24 |

On development cases, raw noise ≥ 2 mm caused release timeouts in every case. The giver reference fixed this
for every smoothing level, and delay had no effect. The best constant offset was zero, which is why
`geometry_best_constant` equals `geometry_common`.

### 5.3 Pilots (development cases; 2.75M transitions each)

| pilot | transitions | fps | losses finite | train success (last 20%) | dev success /144 | resid. mean [mm] | resid. max [mm] | clip [mm] | align sat. | mean resid. x,y,z [mm] |
|---|---|---|---|---|---|---|---|---|---|---|
| combined_clean_ff_s101 | 2,752,512 | 9759 | True | 99.9% | 144 | 5.62 | 13.68 | 0.00 | 0.296 | -0.46, -5.08, -3.35 |
| combined_robust_ff_s101 | 2,752,512 | 9593 | True | 99.7% | 144 | 6.21 | 12.41 | 0.00 | 0.300 | -2.74, -0.23, -5.90 |
| combined_robust_ff_s102 | 2,752,512 | 9244 | True | 100.0% | 144 | 3.88 | 12.33 | 0.00 | 0.301 | -3.41, 1.36, 1.09 |
| combined_robust_history_s101 | 2,752,512 | 9257 | True | 99.7% | 144 | 3.25 | 5.33 | 0.00 | 0.301 | -0.94, -0.03, -2.42 |
| combined_robust_history_s102 | 2,752,512 | 9657 | True | 99.6% | 144 | 6.12 | 10.98 | 0.00 | 0.304 | 0.03, 3.06, 0.60 |
| combined_robust_repeat_s101 | 2,752,512 | 9475 | True | 100.0% | 144 | 3.85 | 9.53 | 0.00 | 0.300 | -2.29, -0.27, -2.33 |
| residual_robust_history_s101 | 2,752,512 | 9060 | True | 76.9% | 120 | 2.42 | 6.39 | 0.00 | 0.000 | 0.11, -0.30, -0.16 |
| residual_robust_history_s102 | 2,752,512 | 8832 | True | 77.2% | 110 | 2.13 | 6.52 | 0.00 | 0.000 | 1.15, 0.84, -0.68 |

Pilots showed finite losses, valid resets and no clipping, so the inherited PPO settings were kept unchanged.

## 6. Held-out results (final suite)

### 6.1 Validation learning curves and selection

![validation learning curves](../../results/v3/figures/learning_curves.png)

| run | selected checkpoint | validation success | collision rate |
|---|---|---|---|
| combined_clean_ff_s11 | step_008028160 | 100.0% | 0.0% |
| combined_clean_ff_s22 | step_010027008 | 100.0% | 0.0% |
| combined_clean_ff_s33 | step_010027008 | 100.0% | 0.0% |
| combined_clean_ff_s44 | step_010027008 | 100.0% | 0.0% |
| combined_clean_ff_s55 | step_010027008 | 100.0% | 0.0% |
| combined_robust_ff_s11 | step_010027008 | 100.0% | 0.0% |
| combined_robust_ff_s22 | step_010027008 | 100.0% | 0.0% |
| combined_robust_ff_s33 | step_010027008 | 100.0% | 0.0% |
| combined_robust_ff_s44 | step_006029312 | 100.0% | 0.0% |
| combined_robust_ff_s55 | step_010027008 | 100.0% | 0.0% |
| combined_robust_history_s11 | step_002031616 | 100.0% | 0.0% |
| combined_robust_history_s22 | step_002031616 | 100.0% | 0.0% |
| combined_robust_history_s33 | step_004030464 | 100.0% | 0.0% |
| combined_robust_history_s44 | step_008028160 | 100.0% | 0.0% |
| combined_robust_history_s55 | step_002031616 | 100.0% | 0.0% |
| combined_robust_repeat_s11 | step_010027008 | 100.0% | 0.0% |
| combined_robust_repeat_s22 | step_008028160 | 100.0% | 0.0% |
| combined_robust_repeat_s33 | step_010027008 | 100.0% | 0.0% |
| residual_robust_history_s11 | step_010027008 | 80.8% | 16.7% |
| residual_robust_history_s22 | step_002031616 | 77.1% | 18.8% |
| residual_robust_history_s33 | step_008028160 | 83.3% | 14.6% |
| residual_robust_history_s44 | step_002031616 | 84.6% | 16.7% |
| residual_robust_history_s55 | step_002031616 | 83.3% | 16.7% |

Every combined run reaches 100% validation success at its selected checkpoint, so selection among tied
candidates fell to the residual-size and latest-step tie-breaks. Robust-history training is not monotone:
seed 11 drops to 8.8% at 8M and seed 55 to
0.0% at 6M (collisions). Residual-only history runs decline after 2–4M
(seed 55: 5.4% at 10M).

### 6.2 Success by condition

Success % over 200 cases per condition (learned rows: mean over training seeds):

| controller | clean | physical only | bias 2mm | bias 5mm | bias 10mm | noise 1mm | noise 2mm | noise 4mm | delay 1step | delay 2step | delay 4step | mixed id | mixed ood |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nominal script | 100.0 | 71.0 | 71.0 | 71.5 | 71.0 | 70.0 | 71.0 | 70.0 | 70.5 | 71.0 | 71.0 | 70.5 | 71.0 |
| geometry, raw estimate | 100.0 | 100.0 | 100.0 | 100.0 | 67.0 | 25.0 | 0.5 | 0.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 |
| geometry, EMA-filtered | 100.0 | 100.0 | 100.0 | 100.0 | 67.5 | 100.0 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 96.0 |
| geometry_common (giver reference) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| geometry_best_constant (= geometry_common) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| geometry_giver (= geometry_common) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| combined, clean-trained FF (selected) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| combined, robust FF (selected) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| combined, robust history (selected) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| residual-only, robust history (selected) | 100.0 | 68.9 | 68.7 | 68.6 | 68.7 | 68.8 | 68.7 | 68.4 | 68.8 | 68.4 | 68.3 | 68.7 | 68.8 |
| combined, robust repeated-current (selected) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| combined, clean-trained FF (final) | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 100.0 | 100.0 | 99.9 | 99.9 | 99.9 | 99.9 | 99.9 | 100.0 |
| combined, robust FF (final) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| combined, robust history (final) | 69.6 | 72.5 | 71.7 | 72.0 | 72.4 | 71.9 | 72.7 | 72.5 | 72.5 | 72.1 | 72.1 | 71.8 | 71.5 |
| residual-only, robust history (final) | 80.0 | 58.6 | 58.4 | 58.4 | 58.9 | 58.6 | 58.8 | 58.4 | 58.7 | 58.5 | 58.5 | 58.4 | 58.8 |
| combined, robust repeated-current (final) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

![severity curves, selected checkpoints](../../results/v3/figures/severity_selected.png)

![severity curves, final checkpoints](../../results/v3/figures/severity_final.png)

### 6.3 Primary and secondary paired effects

| comparison | role | cases | difference [pp] (95% CI) | per seed [pp] |
|---|---|---|---|---|
| **combined_robust_history − combined_robust_ff** | selected | mixed_id | +0.0 [+0.0, +0.0]; 97.5%: [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| combined_robust_history − combined_robust_ff | selected | mixed_ood | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| combined_robust_history − combined_robust_ff | selected | 12 non-clean conditions (equal weight) | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| **combined_robust_history − geometry_best_constant** | selected | mixed_id | +0.0 [+0.0, +0.0]; 97.5%: [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| combined_robust_history − geometry_best_constant | selected | mixed_ood | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| combined_robust_history − geometry_best_constant | selected | 12 non-clean conditions (equal weight) | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| combined_robust_ff − combined_clean_ff | selected | mixed_id | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| combined_robust_ff − combined_clean_ff | selected | mixed_ood | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| combined_robust_ff − combined_clean_ff | selected | 12 non-clean conditions (equal weight) | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| residual_robust_history − nominal | selected | mixed_id | −1.8 [−10.2, +4.4] | +0.0 / −17.0 / +6.5 / +1.5 / +0.0 |
| residual_robust_history − nominal | selected | mixed_ood | −2.2 [−10.7, +4.0] | +0.0 / −17.5 / +6.0 / +1.5 / −1.0 |
| residual_robust_history − nominal | selected | 12 non-clean conditions (equal weight) | −2.1 [−10.5, +4.0] | +0.1 / −17.3 / +6.2 / +1.3 / −1.0 |
| combined_robust_history − geometry_common | selected | mixed_id | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| combined_robust_history − geometry_common | selected | mixed_ood | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| combined_robust_history − geometry_common | selected | 12 non-clean conditions (equal weight) | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| combined_robust_history − combined_robust_repeat | selected | mixed_id | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 |
| combined_robust_history − combined_robust_repeat | selected | mixed_ood | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 |
| combined_robust_history − combined_robust_repeat | selected | 12 non-clean conditions (equal weight) | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 |
| combined_robust_history − combined_robust_ff | final | mixed_id | −28.2 [−56.4, −5.4] | −35.5 / +0.0 / −22.0 / −2.0 / −81.5 |
| combined_robust_history − combined_robust_ff | final | mixed_ood | −28.5 [−57.3, −5.5] | −35.0 / +0.0 / −22.5 / −2.0 / −83.0 |
| combined_robust_history − combined_robust_ff | final | 12 non-clean conditions (equal weight) | −27.9 [−56.0, −5.4] | −33.5 / +0.0 / −22.1 / −2.0 / −81.7 |
| combined_robust_history − geometry_best_constant | final | mixed_id | −28.2 [−56.4, −5.4] | −35.5 / +0.0 / −22.0 / −2.0 / −81.5 |
| combined_robust_history − geometry_best_constant | final | mixed_ood | −28.5 [−57.3, −5.5] | −35.0 / +0.0 / −22.5 / −2.0 / −83.0 |
| combined_robust_history − geometry_best_constant | final | 12 non-clean conditions (equal weight) | −27.9 [−56.0, −5.4] | −33.5 / +0.0 / −22.1 / −2.0 / −81.7 |
| combined_robust_ff − combined_clean_ff | final | mixed_id | +0.1 [+0.0, +0.6] | +0.5 / +0.0 / +0.0 / +0.0 / +0.0 |
| combined_robust_ff − combined_clean_ff | final | mixed_ood | +0.0 [+0.0, +0.0] | +0.0 / +0.0 / +0.0 / +0.0 / +0.0 |
| combined_robust_ff − combined_clean_ff | final | 12 non-clean conditions (equal weight) | +0.1 [+0.0, +0.3] | +0.2 / +0.0 / +0.0 / +0.0 / +0.0 |
| residual_robust_history − nominal | final | mixed_id | −12.1 [−38.4, +5.7] | +0.0 / −11.0 / +7.5 / +5.5 / −62.5 |
| residual_robust_history − nominal | final | mixed_ood | −12.2 [−38.6, +5.8] | +0.0 / −11.0 / +8.0 / +5.0 / −63.0 |
| residual_robust_history − nominal | final | 12 non-clean conditions (equal weight) | −12.2 [−38.6, +5.7] | +0.1 / −11.2 / +8.0 / +5.0 / −62.9 |
| combined_robust_history − geometry_common | final | mixed_id | −28.2 [−56.4, −5.4] | −35.5 / +0.0 / −22.0 / −2.0 / −81.5 |
| combined_robust_history − geometry_common | final | mixed_ood | −28.5 [−57.3, −5.5] | −35.0 / +0.0 / −22.5 / −2.0 / −83.0 |
| combined_robust_history − geometry_common | final | 12 non-clean conditions (equal weight) | −27.9 [−56.0, −5.4] | −33.5 / +0.0 / −22.1 / −2.0 / −81.7 |
| combined_robust_history − combined_robust_repeat | final | mixed_id | −19.2 [−35.5, +0.0] | −35.5 / +0.0 / −22.0 |
| combined_robust_history − combined_robust_repeat | final | mixed_ood | −19.2 [−35.0, +0.0] | −35.0 / +0.0 / −22.5 |
| combined_robust_history − combined_robust_repeat | final | 12 non-clean conditions (equal weight) | −18.5 [−33.8, +0.0] | −33.5 / +0.0 / −22.1 |

![paired effects](../../results/v3/figures/paired_effects.png)

Both primary contrasts are exactly 0 pp with zero-width intervals. Both sides succeed on all 2,600 × 5
seed-case pairs, so the bootstrap has no variation to resample. This is a ceiling, not evidence of
equivalence in harder settings. The same holds for robust − clean feed-forward and for history −
repeated-current. Final checkpoints show the instability of history training (negative effects driven by
seeds 11, 33 and 55), not a benefit.

Per-seed success on the primary conditions:

| family | role | mixed_id per seed | mixed_ood per seed |
|---|---|---|---|
| combined, clean-trained FF | selected | 100.0 / 100.0 / 100.0 / 100.0 / 100.0 | 100.0 / 100.0 / 100.0 / 100.0 / 100.0 |
| combined, clean-trained FF | final | 99.5 / 100.0 / 100.0 / 100.0 / 100.0 | 100.0 / 100.0 / 100.0 / 100.0 / 100.0 |
| combined, robust FF | selected | 100.0 / 100.0 / 100.0 / 100.0 / 100.0 | 100.0 / 100.0 / 100.0 / 100.0 / 100.0 |
| combined, robust FF | final | 100.0 / 100.0 / 100.0 / 100.0 / 100.0 | 100.0 / 100.0 / 100.0 / 100.0 / 100.0 |
| combined, robust history | selected | 100.0 / 100.0 / 100.0 / 100.0 / 100.0 | 100.0 / 100.0 / 100.0 / 100.0 / 100.0 |
| combined, robust history | final | 64.5 / 100.0 / 78.0 / 98.0 / 18.5 | 65.0 / 100.0 / 77.5 / 98.0 / 17.0 |
| residual-only, robust history | selected | 70.5 / 53.5 / 77.0 / 72.0 / 70.5 | 71.0 / 53.5 / 77.0 / 72.5 / 70.0 |
| residual-only, robust history | final | 70.5 / 59.5 / 78.0 / 76.0 / 8.0 | 71.0 / 60.0 / 79.0 / 76.0 / 8.0 |
| combined, robust repeated-current | selected | 100.0 / 100.0 / 100.0 | 100.0 / 100.0 / 100.0 |
| combined, robust repeated-current | final | 100.0 / 100.0 / 100.0 | 100.0 / 100.0 / 100.0 |

### 6.4 Failure breakdown

Terminal outcomes out of 200 (exclusive; learned rows: mean over seeds; selected checkpoints unless marked final).
Collision and drop are also recorded as per-episode flags that can co-occur with other outcomes; those flags
are in `results/v3/summary/family_condition_summary.json`.

| controller | condition | success | prohibited collision | drop | release timeout | episode timeout |
|---|---|---|---|---|---|---|
| nominal script | mixed_id | 141.0 | 52.0 | 2.0 | 0.0 | 5.0 |
| nominal script | mixed_ood | 142.0 | 51.0 | 2.0 | 0.0 | 5.0 |
| geometry, raw estimate | mixed_id | 0.0 | 0.0 | 0.0 | 200.0 | 0.0 |
| geometry, raw estimate | mixed_ood | 0.0 | 3.0 | 0.0 | 197.0 | 0.0 |
| geometry, EMA-filtered | mixed_id | 200.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| geometry, EMA-filtered | mixed_ood | 192.0 | 5.0 | 0.0 | 3.0 | 0.0 |
| geometry_common (giver reference) | mixed_id | 200.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| geometry_common (giver reference) | mixed_ood | 200.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| combined, clean-trained FF | mixed_id | 200.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| combined, clean-trained FF | mixed_ood | 200.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| combined, robust FF | mixed_id | 200.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| combined, robust FF | mixed_ood | 200.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| combined, robust history | mixed_id | 200.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| combined, robust history | mixed_ood | 200.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| residual-only, robust history | mixed_id | 137.4 | 51.6 | 5.6 | 0.0 | 5.4 |
| residual-only, robust history | mixed_ood | 137.6 | 51.8 | 5.6 | 0.0 | 5.0 |
| combined, robust repeated-current | mixed_id | 200.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| combined, robust repeated-current | mixed_ood | 200.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| combined, robust history (final) | mixed_id | 143.6 | 36.6 | 0.8 | 5.0 | 14.0 |
| combined, robust history (final) | mixed_ood | 143.0 | 37.2 | 0.8 | 5.2 | 13.8 |

![failure breakdown](../../results/v3/figures/failure_breakdown.png)

The nominal script and residual-only policies fail mainly by prohibited collisions when the bar starts far
from nominal. This is a physical-offset failure, unrelated to the sensor: their `clean` success is 100%, and
their sensor conditions match `physical_only`. Raw-estimate geometry fails by release-gate timeouts under
noise. Filtered geometry fails by collisions under 10 mm bias.

## 7. Mechanisms

**Memory and zero-policy controls.** Every untrained step-0 policy reproduces its controller on the 65-case
subset: combined profiles 65/65 (identical terminal outcomes to `geometry_common`),
residual-only 29/65 (identical to nominal). The repeated-current control equals real
history at selected checkpoints (both at ceiling). Inference-time interventions on the selected history
policies (65 cases × 5 seeds) changed nothing: combined history 325 successes
unmodified, 325 with frames permuted [4,2,0,3,1], 325
with previous frames replaced by the current one; residual-only history 145 /
145 / 145. Interventions are distribution
shifts, not causal proof. On this subset, at the outcome level, the policies do not depend on the order or
content of past frames.

| policy | seed | unmodified /65 | frames permuted /65 | current frame only /65 |
|---|---|---|---|---|
| combined, robust history | 11 | 65 | 65 | 65 |
| combined, robust history | 22 | 65 | 65 | 65 |
| combined, robust history | 33 | 65 | 65 | 65 |
| combined, robust history | 44 | 65 | 65 | 65 |
| combined, robust history | 55 | 65 | 65 | 65 |
| residual-only, robust history | 11 | 29 | 29 | 29 |
| residual-only, robust history | 22 | 29 | 29 | 29 |
| residual-only, robust history | 33 | 29 | 29 | 29 |
| residual-only, robust history | 44 | 29 | 29 | 29 |
| residual-only, robust history | 55 | 29 | 29 | 29 |

**What the residuals do.** For each selected policy, the episode-mean commanded residual on all non-clean
final cases was regressed on [1, true bar offset, injected sensor bias], per axis:

| family | seed | mean abs residual [mm] | max abs residual [mm] | align. saturation | x intercept [mm] | x slope on true offset | x slope on sensor bias | R² |
|---|---|---|---|---|---|---|---|---|
| combined, clean-trained FF | 11 | 5.71 | 12.53 | 0.320 | -2.65 | +0.016 | +0.001 | 0.38 |
| combined, clean-trained FF | 22 | 4.58 | 12.45 | 0.318 | -2.05 | +0.038 | +0.004 | 0.72 |
| combined, clean-trained FF | 33 | 3.47 | 12.85 | 0.317 | -2.19 | +0.016 | +0.003 | 0.16 |
| combined, clean-trained FF | 44 | 3.89 | 10.51 | 0.319 | -1.13 | +0.030 | -0.003 | 0.72 |
| combined, clean-trained FF | 55 | 2.98 | 14.57 | 0.318 | -1.54 | +0.042 | -0.000 | 0.66 |
| combined, robust FF | 11 | 3.54 | 13.78 | 0.317 | -0.72 | +0.042 | +0.000 | 0.56 |
| combined, robust FF | 22 | 4.94 | 11.15 | 0.318 | -2.64 | +0.015 | +0.006 | 0.13 |
| combined, robust FF | 33 | 3.43 | 14.28 | 0.317 | -0.94 | +0.024 | -0.002 | 0.84 |
| combined, robust FF | 44 | 5.76 | 14.30 | 0.319 | -1.48 | +0.035 | -0.002 | 0.20 |
| combined, robust FF | 55 | 4.21 | 11.36 | 0.317 | -2.20 | +0.030 | +0.001 | 0.41 |
| combined, robust history | 11 | 5.56 | 11.37 | 0.319 | -1.68 | +0.022 | -0.003 | 0.51 |
| combined, robust history | 22 | 2.04 | 4.41 | 0.318 | -0.44 | +0.011 | +0.001 | 0.23 |
| combined, robust history | 33 | 6.49 | 17.18 | 0.321 | -1.31 | -0.057 | +0.008 | 0.38 |
| combined, robust history | 44 | 7.80 | 14.68 | 0.320 | -0.85 | +0.079 | +0.005 | 0.25 |
| combined, robust history | 55 | 4.26 | 6.74 | 0.318 | -2.18 | +0.018 | -0.005 | 0.24 |
| combined, robust repeated-current | 11 | 4.02 | 12.07 | 0.317 | -1.94 | +0.016 | -0.008 | 0.23 |
| combined, robust repeated-current | 22 | 3.94 | 12.17 | 0.318 | -2.61 | +0.059 | -0.003 | 0.85 |
| combined, robust repeated-current | 33 | 3.85 | 10.63 | 0.317 | -1.62 | +0.029 | -0.006 | 0.40 |
| residual-only, robust history | 11 | 5.36 | 10.57 | 0.000 | +0.85 | +0.081 | -0.006 | 0.62 |
| residual-only, robust history | 22 | 5.63 | 19.90 | 0.000 | +2.05 | +0.008 | +0.007 | 0.00 |
| residual-only, robust history | 33 | 4.25 | 10.34 | 0.000 | +4.18 | +0.041 | -0.002 | 0.37 |
| residual-only, robust history | 44 | 2.96 | 13.70 | 0.000 | +0.01 | -0.023 | +0.002 | 0.21 |
| residual-only, robust history | 55 | 3.04 | 17.79 | 0.000 | +0.12 | +0.047 | -0.004 | 0.54 |

![residual vs true offset and sensor bias](../../results/v3/mechanisms/figures/residual_vs_error.png)

Across cases, the episode-mean combined residual is dominated by a constant x-offset (-2.6 to -0.4 mm).
Within an episode the residual does vary with phase (for example it shifts after release; trace figures below),
but that pattern barely changes from case to case. They barely depend
on the injected bias (|slope| ≤ 0.008), so the policies neither follow nor correct
the measurement error. Their mean magnitude is 2.0–7.8 mm (maximum
17.2 mm of the 20 mm bound), with no meaningful workspace clipping (≤ 0.002 mm).
Geometry alignment saturates in 31.7–32.1% of scored steps, the same as for `geometry_common` alone (31.8%).
Paired with `geometry_common` on identical non-clean cases, combined policies have
0 policy-only and 0 geometry-only successes; residual-only
policies have 0 policy-only and 3,762 geometry-only.

**Where the gain comes from.** The robustness comes from the estimator, not from learning. Without the giver
reference, noise defeats the raw estimate at the release gate; EMA filtering repairs noise but not large bias.
The giver reference uses accurate proprioception and the rigid grasp to infer the bar position while it is
held, which is exactly when alignment is computed. Measured estimation error while holding was at most 3.0 mm
(acceptance), far below the 1.5 cm alignment bound. After release, the estimate falls back to the corrupted
sensor (up to 10.7 mm error under `mixed_id`), but by then the receiver already holds the bar. Neither
history nor a constant insertion offset is needed on this suite.

**Traces.** Representative true/raw/estimated trajectories with residual and contact signals (supplementary
6-case trace runs, Section 8):

![geometry_common (giver reference): small constant estimate error while the giver holds, noisy fallback after release](../../results/v3/figures/trace_geometry_common_v3-final-mixed_id-0000.png)

*geometry_common (giver reference): small constant estimate error while the giver holds, noisy fallback after release (case v3-final-mixed_id-0000).*

![geometry_raw: noisy raw estimate; the giver never opens (release-gate timeout)](../../results/v3/figures/trace_geometry_raw_v3-final-mixed_id-0000.png)

*geometry_raw: noisy raw estimate; the giver never opens (release-gate timeout) (case v3-final-mixed_id-0000).*

![combined_robust_history seed 11, selected checkpoint: success](../../results/v3/figures/trace_combined_robust_history_s11__selected_v3-final-mixed_id-0000.png)

*combined_robust_history seed 11, selected checkpoint: success (case v3-final-mixed_id-0000).*

![combined_robust_history seed 55, final checkpoint: residual saturates near the 20 mm bound (collapse)](../../results/v3/figures/trace_combined_robust_history_s55__final_v3-final-mixed_id-0000.png)

*combined_robust_history seed 55, final checkpoint: residual saturates near the 20 mm bound (collapse) (case v3-final-mixed_id-0000).*

![residual_robust_history seed 22, selected checkpoint (on the nominal script)](../../results/v3/figures/trace_residual_robust_history_s22__selected_v3-final-mixed_id-0000.png)

*residual_robust_history seed 22, selected checkpoint (on the nominal script) (case v3-final-mixed_id-0000).*

## 8. Repeatability, traces and videos

**Repeatability (65-case subset, sensitivity check on existing cases).** geometry_common,
geometry_best_constant and the five selected history policies were rerun in three fresh process seeds
(6455601–3) at batch sizes 1 and 23: 2,730 episodes. 2,730 of 2,730 reproduced the original terminal
outcome (batch 256, seed 6455501); per-case sensor parameters were identical in every rerun. The paired effect
history − geometry_common is +0.0 [+0.0, +0.0] pp at batch 1 and +0.0 [+0.0, +0.0] pp at batch 23
(processes averaged within case). This is a ceiling-limited check: it shows stable outcomes at 100%, not
stability of a nonzero effect.

| entry | batch | process seed | success /65 | terminal = original | success = original |
|---|---|---|---|---|---|
| geometry_common | 1 | 6455601 | 65 | 65 | 65 |
| geometry_common | 1 | 6455602 | 65 | 65 | 65 |
| geometry_common | 1 | 6455603 | 65 | 65 | 65 |
| geometry_common | 23 | 6455601 | 65 | 65 | 65 |
| geometry_common | 23 | 6455602 | 65 | 65 | 65 |
| geometry_common | 23 | 6455603 | 65 | 65 | 65 |
| geometry_best_constant | 1 | 6455601 | 65 | 65 | 65 |
| geometry_best_constant | 1 | 6455602 | 65 | 65 | 65 |
| geometry_best_constant | 1 | 6455603 | 65 | 65 | 65 |
| geometry_best_constant | 23 | 6455601 | 65 | 65 | 65 |
| geometry_best_constant | 23 | 6455602 | 65 | 65 | 65 |
| geometry_best_constant | 23 | 6455603 | 65 | 65 | 65 |
| combined_robust_history_s11__selected | 1 | 6455601 | 65 | 65 | 65 |
| combined_robust_history_s11__selected | 1 | 6455602 | 65 | 65 | 65 |
| combined_robust_history_s11__selected | 1 | 6455603 | 65 | 65 | 65 |
| combined_robust_history_s11__selected | 23 | 6455601 | 65 | 65 | 65 |
| combined_robust_history_s11__selected | 23 | 6455602 | 65 | 65 | 65 |
| combined_robust_history_s11__selected | 23 | 6455603 | 65 | 65 | 65 |
| combined_robust_history_s22__selected | 1 | 6455601 | 65 | 65 | 65 |
| combined_robust_history_s22__selected | 1 | 6455602 | 65 | 65 | 65 |
| combined_robust_history_s22__selected | 1 | 6455603 | 65 | 65 | 65 |
| combined_robust_history_s22__selected | 23 | 6455601 | 65 | 65 | 65 |
| combined_robust_history_s22__selected | 23 | 6455602 | 65 | 65 | 65 |
| combined_robust_history_s22__selected | 23 | 6455603 | 65 | 65 | 65 |
| combined_robust_history_s33__selected | 1 | 6455601 | 65 | 65 | 65 |
| combined_robust_history_s33__selected | 1 | 6455602 | 65 | 65 | 65 |
| combined_robust_history_s33__selected | 1 | 6455603 | 65 | 65 | 65 |
| combined_robust_history_s33__selected | 23 | 6455601 | 65 | 65 | 65 |
| combined_robust_history_s33__selected | 23 | 6455602 | 65 | 65 | 65 |
| combined_robust_history_s33__selected | 23 | 6455603 | 65 | 65 | 65 |
| combined_robust_history_s44__selected | 1 | 6455601 | 65 | 65 | 65 |
| combined_robust_history_s44__selected | 1 | 6455602 | 65 | 65 | 65 |
| combined_robust_history_s44__selected | 1 | 6455603 | 65 | 65 | 65 |
| combined_robust_history_s44__selected | 23 | 6455601 | 65 | 65 | 65 |
| combined_robust_history_s44__selected | 23 | 6455602 | 65 | 65 | 65 |
| combined_robust_history_s44__selected | 23 | 6455603 | 65 | 65 | 65 |
| combined_robust_history_s55__selected | 1 | 6455601 | 65 | 65 | 65 |
| combined_robust_history_s55__selected | 1 | 6455602 | 65 | 65 | 65 |
| combined_robust_history_s55__selected | 1 | 6455603 | 65 | 65 | 65 |
| combined_robust_history_s55__selected | 23 | 6455601 | 65 | 65 | 65 |
| combined_robust_history_s55__selected | 23 | 6455602 | 65 | 65 | 65 |
| combined_robust_history_s55__selected | 23 | 6455603 | 65 | 65 | 65 |

**Supplementary traces.** The frozen runtime traces only cases that occupy an environment slot at start-up,
so at batch 256 the final matrix traced only `clean-0000`. The six predeclared trace cases were therefore
re-run for every executed final entry in batches of six (records kept separate from the primary matrix,
`traces6/` in the release). Their terminal outcomes match the batch-256 records in 298 of 300 case-entry pairs;
the differences are combined_robust_history_s11__final on v3-final-mixed_id-0000 (success at batch 6 vs episode_timeout at batch 256); combined_robust_history_s11__final on v3-final-noise_4mm-0000 (success at batch 6 vs episode_timeout at batch 256) (`results/v3/traces6/summary.json`). Batch size and process
change GPU floating-point order, so such single-case flips are expected near decision boundaries.

**Videos.** 8 clips on 5 distinct cases plus a 43 s montage, selected by the
frozen rule in `configs/v3/video_rule.json`. The rule takes the first success and the first failure by case ID
in `mixed_id` and `mixed_ood` for combined_robust_history seed 11 (selected) and geometry_best_constant, side
by side on identical cases, plus one clean baseline, one severe-noise raw-geometry case and one
filtered-vs-giver-reference case. **Neither main-comparison method has a failure in either mixed
condition, so no failure clip exists and none was substituted.** Each clip has a sidecar with case, method,
seed, checkpoint and hashes, camera, 20 Hz real-time playback, and both the evaluation and the single-environment
replay outcome; 0 clips disagree between evaluation and replay. Index:
`results/v3/videos/video_index.json`.

## 9. Compute

Every simulator task ran alone on one A100-SXM4-40GB. Formal training: 23 runs,
7.6 GPU-hours, 230,621,184 transitions
(8,415.0 transitions/s including start-up; 19.9 min per
run). Whole study (acceptance through extras, all attempts): 18.1 GPU-hours over
493 task attempts (`results/v3/compute.json`).

## 10. Answers to the hypotheses

- **H1 (different sensitivities): supported for the deterministic controllers.** Noise defeats the raw
  estimate through the release gate, large bias defeats raw and filtered estimates through collisions, delay
  ≤ 200 ms does nothing, and the nominal script is insensitive to the sensor because it does not use it.
- **H2 (noise-trained residuals): not testable on this suite.** Clean- and noise-trained combined policies
  are both at 100% on every condition.
- **H3 (history): no evidence of benefit.** History equals feed-forward and repeated-current at selected
  checkpoints (ceiling). Interventions on frames do not change outcomes, and history training was the least
  stable (three of five final checkpoints lose 22 pp or more against `geometry_common`).
- **H4 (filtering and the giver reference remove the benefit): supported.** The giver-grasp reference alone
  makes geometry perfect on the held-out suite, leaving no headroom for learning.

## 11. Limitations

- **Ceiling.** The primary contrasts are uninformative because the shared estimator saturates the suite.
  Harder conditions (e.g. bias after release, object motion, larger alignment errors) would be needed to rank
  learned policies. Adding them now, after seeing the results, would be exploratory and require a fresh frozen
  suite.
- **The giver reference is privileged in a specific way.** It assumes a rigid grasp with a known nominal
  offset and accurate giver proprioception. Grasp slip or an unknown grasp offset would break it.
- **Synthetic sensor.** Translation-only bias/noise/delay; no vision, occlusion or orientation error; no real
  robot. Not a sim-to-real result.
- **One object, fixed physics.** The optional physical-transfer extension (mass, friction, size) was not
  performed: the bar's spawn geometry, mass and material are module constants, and validated spawn overrides
  were not implemented before the freeze (`docs/v3/DECISIONS.md`).
- **Five seeds (three for the memory control)** and deterministic evaluation; bootstrap intervals describe
  these seeds and cases.
- **Traces at batch 256** cover only the first wave of cases; representative traces come from a separate
  batch-6 run.
- **Freeze record.** `FREEZE.json` hashed `configs/v3/SUITES.json` before the final suite was written, so
  re-running `v3_prepare.py --final` at `experiment-v3` stops at that hash check. The final suite is verified
  by regenerating it and comparing bytes (`docs/v3/DECISIONS.md`); the tag was not moved.

## 12. Reproducibility and artifacts

Source: branch `study/v3-observation-robustness`; experiment tag `experiment-v3`; delivery tag and release
`v3.0.0` with every checkpoint (step 0, all periodic saves, final, latest, with optimizer and normalizer state),
all raw records (development, validation, final, extras, acceptance, traces), logs, analysis, documents and
videos, plus `release_manifest.json`, `SHA256SUMS`, archive inventories and run/checkpoint/video indices.
Reproduction: [docs/v3/REPRODUCE.md](../../docs/v3/REPRODUCE.md). Fresh-download verification:
[docs/v3/VERIFICATION.md](../../docs/v3/VERIFICATION.md). Decisions with UTC times:
[docs/v3/DECISIONS.md](../../docs/v3/DECISIONS.md).

## References

[1] D. Frau-Alfaro, J. Castaño-Amorós, S. Puente, P. Gil, R. Calandra. "Learning Dexterous Object Handover."
IEEE RO-MAN 2025, pp. 380–387. doi:10.1109/RO-MAN63969.2025.11217592. arXiv:2506.16822.

[2] T. Johannink, S. Bahl, A. Nair, J. Luo, A. Kumar, M. Loskyll, J. A. Ojea, E. Solowjow, S. Levine.
"Residual Reinforcement Learning for Robot Control." IEEE ICRA 2019, pp. 6023–6029. doi:10.1109/ICRA.2019.8794127.

[3] T. Silver, K. Allen, J. Tenenbaum, L. Kaelbling. "Residual Policy Learning." arXiv:1812.06298, 2018.

[4] M. Mittal et al. "Isaac Lab: A GPU-Accelerated Simulation Framework for Multi-Modal Robot Learning."
arXiv:2511.04831, 2025. Software: Isaac Lab v3.0.0; documentation https://isaac-sim.github.io/IsaacLab/.

[5] C. Schwarke, M. Mittal, N. Rudin, D. Hoeller, M. Hutter. "RSL-RL: A Learning Library for Robotics
Research." arXiv:2509.10771, 2025. Software: rsl-rl-lib 5.5.1.

[6] J. Schulman, F. Wolski, P. Dhariwal, A. Radford, O. Klimov. "Proximal Policy Optimization Algorithms."
arXiv:1707.06347, 2017.

[7] CSCI645-Project v2 report and release v2.1.1, https://github.com/ywen0511/CSCI645-Project/releases/tag/v2.1.1.

## Software and AI-assistance disclosure

**Software.** NVIDIA Isaac Sim 6.2.0.0 (PhysX), Isaac Lab v3.0.0 (BSD-3-Clause; Franka assets, differential IK,
contact sensors, Newton Warp renderer, RSL-RL wrapper), RSL-RL 5.5.1 (PPO), PyTorch 2.11, NumPy, Matplotlib,
imageio/FFmpeg, python-pptx. No external datasets or demonstrations were used; all training data are online
simulator transitions.

**AI assistance.** The v3 implementation, acceptance tests, experiments, analysis code, figures, this report,
the slides and the videos were produced by an AI coding agent (Anthropic Claude, operating through Claude Code)
working from the written assignment `V3_EXECUTION.md` on the owner's behalf, on the owner's account and
compute. Decisions are logged with UTC times and evidence in `docs/v3/DECISIONS.md`; every number comes from
checked-in scripts applied to the archived raw records. No course AI-use policy was supplied, so no claim of
compliance with such a policy is made.
