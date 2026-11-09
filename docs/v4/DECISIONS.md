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
