# V4 preregistration — unknown in-grasp object translation

Frozen with `configs/v4/FREEZE.json` and tagged `experiment-v4` before any formal training. The machine-readable
plan is `configs/v4/analysis_plan.json`; this page summarizes it. Development, probe and pilot data were used to
choose ranges, baselines and settings; validation data choose checkpoints only; final data choose nothing.

## Question

Where does a giver-reference controller fail when the true object-to-giver translation is unknown, and do
calibrated geometry, short observation history or learned residuals improve handover in that regime? A measured
failure boundary or a strong geometric solution is an acceptable outcome; a positive RL result is not required.

## Task and physical uncertainty

Two Franka Panda arms with parallel-jaw grippers, Isaac Lab 3.0 / Isaac Sim 6.2 (PhysX), fixed commanded
orientations, an 18 × 3.5 × 3.5 cm bar, bounded XYZ residual PPO (±2 cm per axis) — unchanged from V3. New: the bar's
initial translation inside the giver grasp is a per-episode unknown, produced physically (pinned during settling
while the giver closes at its unshifted hold pose, then held by finger contact alone; the achieved offset is
measured after settling and recorded with the request). Supported axes: x (bar axis) and z (vertical); y is the
finger-closing axis and is re-centred by the fingers. Feasible x range: −7 to +15 mm (−10 mm and beyond touches the
giver palm). Mass, friction, dimensions and orientation are fixed.

## Deployable information (identical for every method)

Corrupted bar translation (per-episode bias, per-step noise, delay; optional EMA), robot proprioception, measured
bar orientation, finger contact forces and the contact phase. No controller reads the sampled offset, the clean
bar pose, the case label or a future measurement; the evaluator and privileged debug logs use ground truth only.
The release gate uses the controller's estimated relative speed and the measured contact forces/orientation for
every geometry-gated method (V3 semantics). The calibrated reference averages (measurement − fixed-transform
kinematic estimate) over the first 0.5 s of the scored episode while the giver holds; the window lies inside the
common schedule (the receiver reaches pre-grasp at 1.0 s) and completion times include it. Learned profiles
observe the same calibrated estimate as their geometric parent.

## Conditions (final: 12 × 200 paired base cases = 2,400; validation: 6 × 40; development: 12 × 24)

| condition | in-grasp offset | sensor | relative to training support |
|---|---|---|---|
| clean | 0 (no joint displacement, no release offset) | none | in support |
| grasp_2mm | x ±2, z ±2 mm (random sign) | none | interpolation |
| grasp_5mm | x ±5, z ±5 mm | none | interpolation (x −5 = support edge) |
| grasp_10mm | x +10, z ±10 mm | none | interpolation in x; z at edge |
| grasp_15mm | x +15, z ±10 mm | none | support corner |
| bias_5mm | 0 | bias ±5 mm per axis | support edge |
| noise_2mm | 0 | noise σ 2 mm | support edge |
| delay_2step | 0 | delay 2 steps (0.1 s) | support edge |
| mixed_id | x U[−5, +15], z U[−10, +10] mm | bias U±5 mm, σ 2 mm, delay 2 | in support |
| mixed_ood | x U[−7, +15], z U[−15, +15] mm | bias U±10 mm, σ 4 mm, delay 4 | extrapolation |
| boundary_x_minus_7 | x −7 mm | none | extrapolation toward the palm |
| boundary_z_15 | z ±15 mm | none | extrapolation in z |

Every non-clean condition also carries the base case's joint start displacement (±2 cm per axis) and release
offset (±0.3 s), shared across conditions. Validation conditions: clean, grasp_10mm, grasp_15mm, bias_5mm, noise_2mm,
mixed_id. Split RNG namespaces 6456101 / 6456201 / 6456301; the final suite is generated only after this freeze
(`configs/v4/FINAL_SUITE.json`).

## Methods

Baselines (development-selected, `configs/v4/development/baseline_selection.json`): nominal trajectory;
historical fixed-transform giver reference (V3 configuration, unchanged); EMA geometry without the giver
reference (α 0.2, 2.5 cm alignment); calibrated giver reference (α 0.2, 0.5 s window, 2.5 cm alignment) = common
parent; best development constant on the parent (selected constant = 0, an exact alias of the calibrated
baseline, evaluated once). Learned (five seeds each: 111, 222, 333, 444, 555; 25 formal runs, 10,027,008
transitions each): combined_clean_ff, combined_robust_ff, combined_robust_history (4 chronological frames),
combined_robust_repeat (current frame ×4), residual_robust_history (parent = nominal trajectory).

## Selection, primary analysis and reporting

- Checkpoints: first save at or after 2, 4, 6, 8, 10M transitions; step 0 never eligible. Validation mean success
  (equal weight per condition) ↓, unsafe-event rate ↑, residual magnitude ↑, latest candidate; values rounded
  to 12 decimals. Selected and final checkpoints are analysed separately.
- Primary: `mixed_id`, selected checkpoints, success difference of combined_robust_history − combined_robust_ff and
  combined_robust_history − best_constant_geometry; paired hierarchical bootstrap over training seeds and base-case
  clusters, 10,000 draws, seed 6456401; 95% and Bonferroni 97.5% intervals. A deterministic baseline is broadcast,
  never resampled as five seeds. Degenerate (ceiling/floor) intervals are labelled; no equivalence claim.
- Everything else is exploratory. Denominator: all scheduled cases; invalid resets count as non-success for every
  method and are reported separately; no exclusions.
- Mechanisms (60 cases = 5 per condition), repeatability (batch 6 and 20 × three process seeds), six supplementary
  trace cases, video rule (`configs/v4/video_rule.json`), stopping rules and the 100 GPU-hour cap: see the plan.
