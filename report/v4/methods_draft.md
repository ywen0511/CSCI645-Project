## 1. Motivation and earlier studies

The project (CSCI 645, Robot Manipulation) studies a bimanual handover in Isaac Sim through Isaac Lab: a giver
Franka Panda holds an 18 × 3.5 × 3.5 cm bar with a parallel-jaw gripper and a receiver Franka must grasp it and hold
it alone, using a nominal trajectory, a training-free geometric coordination module (target alignment, a shared
holding anchor and a contact-gated release) and a bounded XYZ residual learned with PPO (±2 cm per axis). The
original proposal asked whether residual learning on top of geometric coordination improves robustness.

- **V1/V2** (releases v1.0.0, v2.0.0, v2.1.1) found that geometric coordination did almost all of the work; learned
  residuals on top of it were near-constant offsets, and a tuned constant offset matched them.
- **V3** (release v3.0.0) corrupted the bar's translation measurement (bias, noise, delay). A geometry controller that
  infers the bar position from the giver's grasp — `giver TCP + fixed object-to-gripper transform`, used while the
  giver holds — succeeded on all 2,600 held-out cases, and so did every selected learned policy: a ceiling. Its
  report identified the key assumption: the grasp transform is known and rigid.

**V4 removes that assumption.** The bar's initial translation inside the giver grasp is now a per-episode unknown,
produced physically. The question is where the historical fixed-transform reference fails, and whether a calibrated
reference, EMA filtering, a short observation history or learned residuals help in that regime. A measured failure
boundary or a strong geometric solution are both acceptable answers; a positive RL result was not required.

## 2. Task, physical grasp uncertainty and feasibility

Everything except the grasp is unchanged from V3: two Franka arms with fixed commanded hand orientations, differential
IK, a 120 Hz PhysX step and 20 Hz control, an 8 s scored horizon, and the V3 evaluator (success = the receiver alone
holds the bar for 2 s with the giver open and out of contact, no table support, above the drop height and with low
relative speed, without a prohibited collision, drop, release timeout or episode timeout).

**How the offset is produced.** During reset settling the bar is pinned at its nominal start pose plus the case's
joint displacement plus the in-grasp offset, while the giver moves to its *unshifted* hold pose and closes its
fingers. The pin is then removed and only finger contact holds the bar for the last 0.3 s of settling, after which
the start is validated: two-finger giver contact, no table support, low speed, no prohibited contact, and both the
joint displacement and the achieved in-grasp offset within 8 mm of the request. There is no weld and no teleport
in scored time. The achieved offset (`bar position − (giver TCP + nominal grasp vector)`) is recorded for every case.

**Feasibility (development probe, 132 cases).** The finger-closing axis (y) is not a supported axis: the fingers
re-centre the bar. Toward the giver palm (−x) the bar end touches the hand at −10 mm (3 of 4 resets invalid) and
−15 mm (4 of 4), but −7 mm is valid; toward the receiver (+x) +15 mm settles stably; z ±15 mm is stable. Achieved
offsets track requests within about 1 mm. The supported region is therefore x ∈ [−7, +15] mm, z ∈ [−15, +15] mm.

## 3. Controllers, information access and calibration

Every controller receives the same deployable channels: the corrupted bar translation (per-episode bias, per-step
noise and delay, optionally EMA-filtered), robot proprioception, the measured bar orientation, finger contact forces
and the contact phase. No controller reads the sampled offset, the clean bar position, the case label or a future
measurement; the evaluator and privileged debug logs use ground truth only (acceptance A6/A8 verify this by
perturbing the privileged tensors during episodes — controller traces stay bit-identical).

- **Fixed-transform reference (historical, V3).** While the giver holds the bar with both fingers, the bar position
  is `giver TCP + R(bar) · nominal grasp vector`. An unknown in-grasp offset becomes an equal, undetected estimate
  error.
- **Calibrated reference.** During the first 0.5 s of the scored episode (10 control frames, while the giver holds),
  the controller averages `measurement − fixed-transform estimate` in the giver-hand frame and then adds that mean
  to the kinematic estimate. This removes the in-grasp offset but inherits the sensor bias, and averages noise by
  √10. The window lies inside the common schedule (the receiver reaches pre-grasp at 1.0 s), so no method's timing
  changes; completion times include it.
- **EMA geometry.** The raw estimate filtered by an EMA (α = 0.2), without any giver reference. It is unaffected by
  the in-grasp offset but sees the sensor bias directly and lags.
- **Learned profiles.** The bounded PPO residual is added to the common geometric parent (the calibrated reference
  with a 2.5 cm alignment bound) or, for the residual-only profile, to the nominal trajectory. All learned profiles
  observe the parent's calibrated estimate.

## 4. Protocol

**Development (not held-out evidence).** Two registered baseline grids (round 1: 31 configurations; round 2: 32 ≤ 36)
on 288 development cases selected the baselines by success, then unsafe events, correction magnitude and completion
time, on the six validation-like strata. Round 1 used an x support of [−5, +10] mm and left the strongest baselines
at the ceiling on `mixed_id`; because the research question concerns the fixed-transform failure regime (x ≥ +7 mm),
round 2 widened the support to the full feasible +x range (+15 mm) before any training. Every round and decision is
logged in `docs/v4/DECISIONS.md`.

**Pilots and freeze.** Four pilots (5.5M transitions each; 23.66M total with smoke runs and a killed packed attempt,
under the 24M cap) showed stable training and no reason to change the V3 PPO settings. The protocol was frozen
(`configs/v4/FREEZE.json`, tag `experiment-v4`) before formal training; the final suite was generated afterwards by
the frozen generator. Preregistration: `docs/v4/PREREGISTRATION.md`; machine-readable plan: `configs/v4/analysis_plan.json`.

## Software and AI-assistance disclosure

**Software.** NVIDIA Isaac Sim 6.2.0.0 (PhysX), Isaac Lab v3.0.0, RSL-RL 5.5.1 (PPO), PyTorch 2.11, NumPy,
Matplotlib, imageio/FFmpeg, python-pptx. No external datasets or demonstrations; all training data are simulator
transitions.

**AI assistance.** The V4 implementation, acceptance tests, experiments, analysis code, figures, this report, the
slides and the videos were produced by an AI coding agent (Anthropic Claude, operating through Claude Code) working
from `POST_V3_EXECUTION.md` and `V4_REMAINING.md` on the owner's behalf, on the owner's account and compute. The
owner's own CPU workflow guards (`docs/v4/CPU_REVIEW.md`) were merged during the study. Decisions are logged with
UTC times in `docs/v4/DECISIONS.md`; every measured number comes from checked-in scripts applied to the released raw
records (`results/v4/number_audit.json`).
