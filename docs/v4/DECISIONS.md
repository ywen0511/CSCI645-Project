# V4 decision log (uncertain giver grasp)

Times are UTC from `date -u` on the workstation. Development decisions precede the freeze; nothing here was
chosen from validation or final outcomes.

## 2026-11-09 15:20 — branch and scope

- Branch `study/v4-grasp-uncertainty` started from maintenance commit `3ae95e7` (Stage A tooling with CPU
  evidence, itself on `4d7beb3` = `study/v3-observation-robustness`). The verified maintenance commit is merged
  into this branch before the freeze (no history rewrite). The `experiment-v3` checkout is never modified.
- Mandatory scope only: static unknown in-grasp translation. The optional dynamic-slip experiment is
  `not_performed` unless the mandatory study and its delivery are secure within 5% of the compute cap.

## 2026-11-09 15:40 — simulator extension (opt-in, V3 defaults unchanged)

- `grasp_uncertainty`: each evaluation case carries `grasp_offset_xyz_m`. During settling stages 1–2 the
  object is pinned at nominal + joint displacement + grasp offset while the giver closes at its *unshifted*
  hold pose; stage 3 removes the pin, so only finger contact holds the bar. The achieved offset is measured at
  the end of settling (`object position − (giver TCP + nominal grasp vector)`) and recorded with the request.
  A new reset check rejects |achieved − requested| ≥ 8 mm (same tolerance as the joint displacement check).
  No weld, no scored-time teleport, no controller access to the true offset.
- `giver_calibration_window_s` (runtime field): the calibrated giver reference averages
  `measurement − fixed-transform kinematic estimate` in the giver-hand frame over the first N scored frames
  (N = window / 0.05 s) while both giver fingers are in contact, then adds that mean to the kinematic estimate.
  The measurement is the corrupted translation before EMA. Before the window closes the fixed transform is used.
  The window lies inside the common schedule (receiver pre-grasp at 1.0 s), so no method's schedule changes;
  completion times are measured from the same t = 0 and include the window.
- Idle environments (evaluation queue exhausted) are pinned without the grasp offset; they are never recorded.
  This makes the true offset tensor unused after settling, which the privileged-perturbation check exploits.
- V3 config hashes are unchanged (new fields are omitted from the hash at their defaults).

## 2026-11-09 15:48 — development feasibility probe (132 cases, development seed namespace, key "probe")

Grid of fixed in-grasp offsets (x, z single-axis −15…+15 mm; y ±2/±5 mm; xz diagonals) on four base cases,
clean sensor. Evidence: `results/v4/development/probe_summary.json`.

- **y (finger-closing axis) is not a supported axis**: the fingers re-centre the bar (achieved y ≈ −0.2 mm for
  requested ±5 mm).
- **x toward the giver palm is physically limited**: −10 mm failed the reset (prohibited contact of the bar end
  with the giver hand) in 3 of 4 cases, −15 mm in 4 of 4; −7 mm was valid in 4 of 4. +15 mm (toward the
  receiver) settled stably in 4 of 4.
- z ±15 mm settled stably. Achieved offsets track requests within ≈1 mm (nominal grasp itself sits at
  ≈ +0.7 mm x, +0.4 mm z).
- With the historical fixed transform, +x offsets ≥ 7 mm caused prohibited receiver collisions (2/4 at +7,
  4/4 at +10 and +15); z offsets up to ±15 mm did not hurt it. With a clean sensor the calibrated reference
  reproduced the clean-truth geometry exactly (113/132 each with a 1.5 cm alignment bound).

Decisions from the probe (before any development-suite evaluation):

- Supported axes: x and z. Training support (robust profiles): x uniform in [−5, +10] mm, z uniform in
  [−10, +10] mm, y = 0, zero with probability 0.25 — asymmetric in x because of the palm limit.
- Severities 2, 5 and 10 mm (random sign on x and z), except that the 10 mm severity uses x = +10 mm only (−10 mm
  is infeasible) and random-sign z = ±10 mm.
- Boundary checks beyond the training support: x = +15 mm, x = −7 mm, z = ±15 mm.
- Condition table, validation subset and training-support labels: `src/csci645_handover/v4_protocol.py`.

## 2026-11-09 15:51 — registered development baseline grid

`configs/v4/development/baseline_grid.json` (committed before evaluation): nominal plus 30 geometry
configurations = EMA α ∈ {1.0, 0.5, 0.2} × reference ∈ {none, fixed transform, calibrated 0.1/0.25/0.5 s} ×
alignment bound ∈ {1.5, 2.0} cm (31 ≤ 36). The historical fixed-transform baseline is the unchanged V3
`geometry_common` configuration (α = 1, fixed transform, 1.5 cm). The constant-residual search (x ∈ {−10, −5, 0,
+5, +10} mm × z ∈ {−5, 0, +5} mm, y = 0; 15 offsets, ±2 cm bound) is applied to the selected common parent
afterwards and logged separately. Selection strata are the six validation conditions of the development suite.

## 2026-11-09 16:05 — development round 1 result and round 2 (support covers the full feasible +x range)

Round 1 (`configs/v4/development/round1/`, 31 registered configurations × 288 development cases, source
`901f7c8`; summary `results/v4/development/round1_summary.json`; 0 invalid resets, 0 failed tasks):

- The historical fixed transform fails where the probe predicted: grasp_10mm 7/24, x = +15 mm 3/24 (prohibited
  receiver collisions), but mixed_id 23/24 because few uniform draws in [−5, +10] mm exceed +7 mm.
- Calibrated references (any window/α) and EMA α = 0.2 without the giver reference reach 24/24 on every
  validation-like stratum including mixed_id with a 2.0 cm alignment bound; they fail only on mixed_ood and
  x = +15 mm (21/24, alignment bound saturated). A 1.5 cm bound was never better than 2.0 cm on any condition.
- Raw estimate (α = 1, no giver reference) fails on noise (0/24) as in V3.

The predeclared primary condition (mixed_id) was therefore at the ceiling for the strongest baselines, which
would make the primary contrasts degenerate (the V3 failure mode). The research question concerns the regime
where the giver reference fails (x ≥ +7 mm), which the probe shows is physically feasible up to +15 mm. Decision
(before any training, validation or final data exist):

- Training support and mixed_id grasp range: x ∈ [−5, +15] mm (full feasible range toward the receiver),
  z ∈ [−10, +10] mm. New severity `grasp_15mm` (x = +15 mm, z = ±10 mm random sign) replaces the round-1
  boundary condition x = +15 mm, which is now inside the support. Validation conditions: clean, grasp_10mm,
  grasp_15mm, bias_5mm, noise_2mm, mixed_id. Sensor error distributions are unchanged.
- Grid round 2 (re-registered before evaluation): the dominated 1.5 cm bound is replaced by 2.5 cm
  (α × reference × {2.0, 2.5} cm = 30) plus nominal and the unchanged historical V3 configuration
  (α = 1, fixed transform, 1.5 cm): 32 ≤ 36 configurations. Whether 2.5 cm is physically valid is measured
  (collisions count as unsafe events in the selection rule).
- Not done: no condition was removed because a method failed it; no sensor channel was disabled for any method.

## 2026-11-09 16:20 — development round 2 result and baseline selection

Round 2 (32 registered configurations × 288 development cases, source `1890ac1`, summary
`results/v4/development/round2_summary.json`; 0 invalid resets). Every evaluation process exited 0 and every
matrix status is complete, but the runner ledger marks the six tasks as failed: I had not regenerated
`results/v4/jobs/development.json` after re-registering the grid, so the runner checked round-1 output names
(1.5 cm entries) that no longer exist. The records themselves are complete and provenance-checked by
`eval_matrix.py`; the manifest is regenerated now. Logged, not hidden.

- Historical fixed transform (V3 configuration): grasp_10mm 7/24, grasp_15mm 3/24, mixed_id 17/24 — the measured
  failure boundary of the giver reference under unknown in-grasp offsets (prohibited receiver collisions).
- Calibrated references with a 2.5 cm bound and EMA α = 0.2 without the giver reference: 24/24 on all six
  validation strata and mixed_id; failures remain only on mixed_ood (21–23/24).
- Raw estimate (α = 1, no giver reference): noise_2mm 0/24, mixed_id 0/24.

Selection by the registered rule (`configs/v4/development/baseline_selection.json`):
common parent and `geometry_calibrated` = `ema0p2_cal050_a25` (EMA α 0.2, calibrated reference, 0.5 s window,
2.5 cm alignment bound); `geometry_ema` = `ema0p2_none_a25`; `geometry_fixed` = `ema1p0_fixed_a15`
(historical, not tuned); `nominal`. The calibrated 0.5 s window with α ∈ {0.2, 0.5, 1.0} tie on every key to 12
digits (the EMA only acts after release, when the giver reference is no longer used); the registered final
tie-break (candidate ID) selects α = 0.2.

Not all development cases are at the ceiling (mixed_ood fails for every configuration; the historical reference
fails widely), so no further expansion of uncertainty is made. The primary condition may be near the ceiling for
the calibrated parent; that is a finding to report, not a reason to redesign.

## 2026-11-09 16:21 — constant search, training protocols and acceptance plan

- Constant-residual search on the parent: 15 offsets (x ∈ {−10, −5, 0, 5, 10} mm × z ∈ {−5, 0, 5} mm) on the
  development suite (`configs/v4/development/matrices_constant/constant_search.json`).
- Draft training protocols (`configs/v4/training/`, pilots `configs/v4/pilot/`): all profiles share the parent
  estimator (α 0.2, giver reference, 0.5 s calibration) and alignment bound 2.5 cm; V3 PPO settings, rollout
  (1,024 envs × 32 steps), curriculum of joint start displacement, actor zero-mean initialization and 10M budget
  (10,027,008 realized). Robust profiles: sensor as V3 (bias ≤ 5 mm, noise ≤ 2 mm, delay ≤ 2 steps, 25% clean)
  and in-grasp offset uniform over the training support (25% zero). History = 4 frames.
- Acceptance checks A1–A9 (`scripts/v4_acceptance_setup.py`).

## 2026-11-09 16:45 — acceptance (first pass) and the table-support control fix

All 43 acceptance tasks ran (source `f261da3`); judge: `results/v4/acceptance/acceptance.json`. Passed: V3 path
identical to published V3 records (A1), zero-offset V4 path identical (A2), layout batch 1/8/72/72-reversed
72/72 agreement with identical exogenous parameters (A4; calibration estimates differ by ≤ 0.21 mm through
physics), reset leakage 288/288 agreement over 18 consecutive episodes per environment (A5; ≤ 0.38 mm),
privileged perturbation leaves every controller trace field and every outcome identical for the parent and a
smoke policy (A6, A8), step-0 (zero-mean) checkpoints of all five profiles reproduce their parents (A7), smoke
resume for all five profiles (counters, optimizer, normalizer, RNG), evaluation resume/tamper (A9).

Failed: A3 table support — 5/16 (nominal) and 8/16 (parent) "successes" plus 8 invalid resets. Cause: the
negative-control harness placed the support table under the nominal bar position, ignoring the in-grasp offset.
With z = +10 mm the bar sat 10 mm above the table (so the control's premise did not hold and those were genuine
receiver holds); with z = −10 mm the table intersected the bar (invalid resets). The other two negative controls
(no receiver; giver keeps holding) produced 0 successes. Fix in `_begin_settle` (table_support branch only):
place the table under nominal + joint offset + in-grasp offset. A1–A3 are rerun at the fixed commit; the rest of
the code is unchanged by the fix.

## 2026-11-09 17:03 — pilots run one at a time

Four pilots were first packed on one GPU with two acceptance evaluations: ≈1,100 transitions/s each (≈4,400/s
in total) versus ≈8,900/s for one V3 training process on the same hardware. The packed job was killed after 4
PPO iterations per pilot (≤ 0.66M transitions in total, counted against the 24M pilot cap; partial outputs kept
under `v4/pilots/`) and the pilots were restarted one at a time in a new runs root. Pilot total ≤ 23.67M.
Formal training also runs one process per GPU.

## 2026-11-10 01:40 — pilots reviewed; no change to training settings

Four pilots (5,505,024 transitions each, seeds 901/902, `results/v4/pilots/pilot_eval_summary.json`; source
`5089373`), evaluated on the six validation-like development strata at 2M, 4M and final: the combined robust
feed-forward and history pilots reach 24/24 in every stratum at every checkpoint (one 23/24 at 4M), i.e. the
level of their calibrated parent; the residual-only history pilot (nominal parent) reaches 12–24/24 (mixed_id
15/24). Training was stable (no collapse, no non-finite values, ~8,300 transitions/s alone on one A100).
Pilot transitions: 22,020,096 + smoke 983,040 + killed packed attempt ≤ 655,360 = ≤ 23,658,496 ≤ 24M cap.
Decision: keep the V3 PPO, network, rollout and curriculum settings; freeze. (The session was paused for about
eight hours after the pilots finished; nothing ran in between.)
