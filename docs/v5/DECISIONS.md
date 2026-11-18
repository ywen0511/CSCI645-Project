# V5 decision log

Append-only. Each entry: date, decision, reason, evidence.

## 2026-11-17 — CPU preparation (owner's machine, no GPU or simulator)

- **Scope.** The owner asked for three tiers: CPU-only fixes and analysis now; a matched
  calibration ablation (Study A) and a dynamic-slip study (Study B) on remote GPU later,
  with a complete public release. CPU work is on branch `study/v5-calibration-slip`.
- **Failure taxonomy.** The proposal promised drop/collision rates, completion time and a
  misalignment / premature-release / conflicting-motion breakdown. V1 reported them; the V4
  synthesis did not. `scripts/v5_failure_taxonomy.py` derives them from the public
  v4.0.0 `raw-final.tar.gz` (SHA-256 checked) without changing published V4 outputs.
  Flags are reported among failed valid-reset episodes because they are non-exclusive.
- **AI disclosure.** The owner confirmed all AI assistance was Anthropic Claude via Claude
  Code. The V4 overview, REVIEW.md and DEFENSE_NOTES.md had named Codex in error; corrected.
  The already published v4.0.2 overview PDF is immutable; the correction is recorded in
  REVIEW.md and will ship in v5.0.0.
- **Overview.** Added the failure section, the V3 residual-only counter-example
  (68.7% vs 70.5%), ManipTrans (cited in the proposal, V1 and V2 but dropped in V4), and
  V5 pointers. PDF links now target `main`. The overview grew from 6 to 7 pages.
- **Study A design.** 2 x 2 x 2 factorial (reference fixed/cal050 x EMA 1.0/0.2 x bound
  15/25 mm) of training-free geometry, so the V4 confound (three settings changed at once)
  is separated. Fresh suite: V4 condition definitions, split seed 6457301 (6456501 was
  already V4's evaluation-process seed), 200 cases x 12 conditions. Primary contrasts at
  matched alpha 0.2 / bound 25 mm on mixed_id and grasp_15mm, Bonferroni 97.5%, case-level
  paired bootstrap (single deterministic controller per arm, so no seed level). Frozen in
  `configs/v5/calibration/FREEZE.json` before any simulation.
- **Study B design principles** (details left to the GPU agent's feasibility probe):
  physical slip only, onset after the calibration window, a continuous re-estimating
  geometric baseline as the strong comparator, learned residuals on the V4 calibrated
  parent, V4 selection rule, freeze before final evaluation, explicit infeasibility exit.

## 2026-11-17 21:38Z — Study A executed (remote GPU agent, Claude Code)

- **Compute.** Only `gpu_large` host gc216 (4 x A100-SXM4-80GB) and gc214 had free GPUs; dgx047 (V4's
  host) was fully occupied with 300+ queued jobs. A100-80GB is the same architecture as V4's A100-40GB;
  simulator, driver bundle and environment are unchanged. Each job requests one exclusive GPU.
- **Freeze check** `scripts/v5_make_calibration_study.py --check` printed PASS. The simulator source of
  `13cda3a` equals `experiment-v4` (`git diff --stat experiment-v4 HEAD -- src scripts/eval_matrix.py
  configs/v2/protocol.json scripts/train.py` is empty). Tagged `experiment-v5a` = `13cda3a`; evaluated from a
  fresh clone of that tag (0 dirty files).
- **Commands** (in the clone, through `scripts/cluster_v2/gpu_run.sh`; `--dry-run` of all three matrices first,
  inside the same GPU job because the dry run boots Omniverse Kit):
  `eval_matrix.py --matrix configs/v5/calibration/matrix_ema1p0.json --output <runs>/v5/calibration/primary --seed 6457501`,
  then `matrix_ema0p2.json` into the same directory, sequentially in the same job (the two primary matrices
  share one output directory, so they were not run concurrently); `matrix_repeat_ema0p2.json --output
  <runs>/v5/calibration/repeat --seed 6457502` in a second job.
- **Acceptance gates passed.** 10 entries x 2,400 records, 0 infrastructure errors, `source_dirty` false,
  source `13cda3a`. Anchors: `ema1p0_fixed_a15` config `ff52ebeb...` / controller `c822250e...` and
  `ema0p2_cal050_a25` config `8b3a0a9d...` / controller `96a1ffc4...`, exactly the V4 values.
- **Analysis** `scripts/v5_calibration_analysis.py`, unedited. A1 (mixed_id) +29.5 pp, Bonferroni 97.5% CI
  [+22.5, +36.5]; A2 (grasp_15mm) +93.0 pp [+88.5, +96.5]: both support a calibration-only improvement under
  the frozen rule. Exploratory: EMA alpha had exactly zero effect (identical terminal outcomes in every
  cell); the alignment bound added +3.2 pp on mixed_id. Repeat process: 2,400/2,400 matching outcomes for both
  repeated configurations. Taxonomy by the new reader `scripts/v5_taxonomy_records.py` (V4 outputs untouched).
- Invalid resets differ slightly between configurations (5 to 8 of 2,400), all counted as failures; they
  depend on the batch context of the shared PhysX scene, as recorded in V4.

## 2026-11-17 21:38Z — Study B slip mechanism, development probe round 1

- Mechanism (option a, `src/csci645_handover/core/slip.py`): during `[onset, onset + duration)` the giver's
  finger target is relaxed to a chosen squeeze and a PID-regulated force along the bar axis acts at the bar's
  centre of mass (min-jerk displacement profile); then the finger target returns to closed while the force
  holds for `regrip_s`; afterwards the force is zero. Only the x component of the force is applied; the grip
  carries the weight. No pose or velocity write in the scored phase. Opt-in config fields, default off; with
  the new code the V4 `geometry_calibrated` configuration still hashes to `8b3a0a9d...` (probe records).
- Probe (commit `8ad36b3`; 88 development cases: targets x in {-7,-5,-2,+2,+5,+10,+15} mm x onsets
  {0.70, 1.05, 1.40} s x 4 base cases, plus no-slip controls), mechanisms M1-M3 with relaxed squeeze commands
  6/12/20 N (the closed command measures ~17.3 N per finger):
  * the bar-axis target was tracked (x error <= 0.6 mm), but the bar sagged vertically while sliding under the
    relaxed squeeze (z -3 to -10 mm at M1, -2 to -3 mm at M2, -1 to -2 mm at M3), so most slips missed the
    1.5 mm tolerance (x and z). Negative slips toward the palm (-5, -7 mm) tipped the bar (z -10 to -30 mm,
    drops) at every setting.
  * No-slip equivalence: identical outcomes, record fields and bitwise-identical trace positions (3,492
    position samples), mechanism off vs on.
  * Negative controls (no receiver, giver holds, table support) with slip: 0 successes.
- Decision: round 2 keeps the squeeze near/at the closed command (M4 ~80%, M5/M6 full) with a larger force
  cap, because the sag is the expected Coulomb effect of sliding under a small normal force.

## 2026-11-17 21:46Z — Study B probe round 2, mechanism and feasible range fixed

- Round 2 (commit `b664646`, same 88 probe cases): M4 (squeeze command 28 N, gains kp 12000/kd 80/ki 150000,
  cap 70 N), M5 (full squeeze, same gains, cap 90 N), M6 (full squeeze, round-1 gains kp 6000/kd 60/ki 60000,
  cap 90 N). Per-target valid slips (x and z within 1.5 mm; 12 episodes per target):
  M6: -7 mm 1/12, -5 mm 3/12, -2 mm 12/12, +2 mm 12/12, +5 mm 12/12, +10 mm 12/12, +15 mm 9/12.
  M4 kept {-2, +2, +5}; M5 kept {+2, +5}. Summary: `results/v5/slip/probe/summary.json`
  (`scripts/v5_probe_summary.py`).
- **Mechanism M6 selected** (most accepted targets). With `grip_force_n` = 35 N the relaxed finger target equals
  the closed command, so the giver's squeeze is unchanged: in effect option (b), a regulated bar-axis force
  (peak 35-51 N at accepted targets) that overcomes finger friction. No receiver contact before t_grasp and no
  drop at any accepted target; negative controls with slip: 0 successes in all three; no-slip control unchanged
  (bitwise-identical trace positions for both rounds).
- **Feasible cumulative in-grasp x range [-2, +10] mm.** Dropped: +15 mm (about 2 mm vertical sag while sliding;
  9/12 valid) and -5 / -7 mm (toward the giver palm: tipping and palm contact), consistent with the V4 palm-side
  limit. Probe GPU use about 0.2 GPU-hours (cap 6).
- **Condition adjustments (only to the feasible range, before any suite was frozen):** `slip_neg_5` becomes
  `slip_neg_2` (-2 mm); `slip_mixed_id` (raw slip uniform [-5, +10] mm) and `slip_mixed_ood` (raw [-7, +15] mm)
  are clamped so that start x + slip x stays in [-2, +10] mm (clamp: slip = clip(start + raw, -2, +10) - start;
  `slip_clamped` and `slip_requested_x_m` are recorded per case). Static start offsets are not clamped (no-slip
  conditions keep the V4 rules). Slip duration 0.25 s, onset uniform [0.7, 1.4] s keyed per base case, so slips
  end by 1.75 s (1.65 s plus the 0.1 s hold), before the 2.0 s receiver grasp.
- Development grid (`scripts/v5_slip_dev.py grid`): 192 development cases (8 conditions x 24, seed 6458101);
  14 training-free candidates: nominal, V4 fixed/EMA/calibrated geometry, six `geometry_tracking` settings
  (EMA weight 0.05/0.1/0.2/0.4 at 25 mm bound, 0.2/0.4 at 35 mm) and four constant x offsets (+-2, +-4 mm) on the
  calibrated parent. Ranking: V4 rule on the four V5 validation conditions (development cases only).

## 2026-11-17 21:54Z — Development round 1 revealed that slip feasibility depends on slide direction

- Development round 1 (commit `678d641`, 192 cases, 14 candidates; records kept for the release) showed that
  slip validity depends on the slide itself, not only on the final in-grasp position (the probe started every
  slide at offset 0, so it could not separate the two). Pooled over all 14 controllers (slip validity is set
  before the receiver touches the bar): slides toward the giver palm beyond -2.5 mm: 0 of 476 valid; -2.5..0 mm:
  476 of 532 (89.5%); slides toward the receiver 0..2.5 mm: 84/84; 2.5..5 mm: 406/406; 5..8 mm: 112/112;
  8..10 mm: 354/378 (93.7%). `slip_after_offset` (+10 mm start, -10 mm slide) failed 24/24 (the bar dropped
  about 11 mm while sliding back).
- **Feasible slip redefined before any freeze:** slides toward the receiver of 0..+8 mm (>= 95% valid in all
  development evidence), with the cumulative offset start + slide inside the V4 static feasible range
  [-7, +15] mm. Conditions adjusted only to this range: `slip_pos_10` -> `slip_pos_8`; `slip_neg_5` dropped
  (slides toward the palm are infeasible; no feasible version exists); `slip_after_offset` = start -5 mm (palm-side
  static offset), slide +8 mm; `slip_mixed_id` and `slip_mixed_ood` slides uniform [0, +8] mm (out-of-distribution
  only in start offsets and sensor corruption, because larger slides are infeasible). Study B therefore has seven
  final conditions. Training slip: probability 0.5, slide uniform [0, +8] mm, cumulative bound [-7, +15] mm.
- Round-1 outcome on the four selection strata (informative only; not used for the final design beyond
  feasibility): the V4 one-shot calibrated parent failed every +10 mm slide (0/24, receiver collision with the
  slid bar); every `geometry_tracking` setting and the +4 mm constant offset solved it (24/24); the top settings
  tied at 94.8% strata success.
- **`geometry_best` tie-break:** the V4 rule measures correction magnitude differently for geometry (alignment
  correction) and for constant offsets (|c|); V4 never ranked the two families against each other. For the
  cross-family `geometry_best` the common total correction mean |alignment correction + c| is used; within a
  family the V4 definitions are kept.
- The three pilots launched at 21:48Z (seed 901) used the superseded slide distribution; they are kept and
  labelled `pilot_r1`; pilots are rerun (`pilot_r2`) with the final training distribution.

## 2026-11-17 22:02Z — Development round 2, pilots, Study B freeze (`experiment-v5b`)

- Development round 2 (commit `a88da75`, 168 cases, 7 conditions x 24): `geometry_tracking` =
  `tracking_a005_b25` (EMA weight 0.05, bound 25 mm); best constant = calibrated parent + 4 mm in x;
  `geometry_best` = `tracking_a005_b25` (tied on success 98.96% and unsafe 0% with the +4 mm constant, EMA geometry
  and three other tracking settings; the smallest total correction decides). Strata success: calibrated parent
  96.9%, fixed geometry 70.8%, nominal 56.3%. One invalid slip per controller in 96 strata cases.
  `configs/v5/slip/development/baseline_selection.json`.
- Pilots `pilot_r2` (seed 901, 2,031,616 transitions, final training distribution): training-episode success
  0.96 -> 0.98 (feed-forward), 0.88 -> 0.97 (history), 0.95 -> 0.98 (repeat); 8,160-8,545 transitions/s, so a
  formal run takes about 20 minutes. Learning curves move; no pilot is used for any claim
  (`results/v5/slip/pilot/summary_r2.json`).
- **Freeze** (`configs/v5/slip/FREEZE.json`, 68 inputs, before any Study B final evaluation): suites (validation
  160, final 1,400, mechanism subset 60, V4 final suite with zero slip 2,400), training protocols, baseline
  selection, analysis plan, pre-training matrices and runner manifests, the generator of the post-selection
  matrices, the analysis script (tested on synthetic records only), the simulator source. Primary: B1 history - FF
  and B2 history - geometry_best on `slip_mixed_id`, selected checkpoints, paired seed x case bootstrap
  (10,000, seed 6458401), superiority only if the Bonferroni 97.5% lower bound > 0.
- Checkpoint selection (frozen): ten candidates at the first checkpoints at/after each 1 M transitions; step 0
  never eligible; V4 key on the four validation conditions. Unlike V4 (which aborted on invalid resets),
  invalid resets and invalid slips count as failures in the all-scheduled denominator, because the slip
  mechanism has a small, method-independent failure rate.

## 2026-11-18 05:50Z — Checkpoint selection; post-selection manifest path fix

- **Validation** (15 runs x 11 checkpoints x 160 cases, `results/v5/jobs/validation.json`) completed with no failed
  task. `v5_slip_study.py select` (frozen V4 key) chose: feed-forward 5.0/7.0/10.0/8.0/9.0 M, history
  5.0/9.0/4.0/5.0/5.0 M, repeat 10.0/7.0/10.0/9.0/10.0 M transitions (seeds 111-555). Validation success of the
  selected checkpoints is 95.6-96.3% for every run; `results/v5/slip/selection/`.
- **First submission of the post-selection manifests failed before any simulation** (38 of 38 tasks,
  `FileNotFoundError` reading the matrix). The frozen generator writes post-selection matrices into the delivery
  checkout but addressed them relative to the execution checkout, which is the frozen `experiment-v5b` tag and
  cannot contain them. Fix without touching any freeze input: `scripts/v5_manifest_paths.py` prefixes those matrix
  paths with `$DELIVERY/` (the V4 convention, `scripts/v4_manifests.py`). Matrix contents, suites, protocols,
  checkpoints and seeds are unchanged; `v5_slip_study.py check` still passes. The failed attempts stay in the
  runner records (attempt 1 of each task).
