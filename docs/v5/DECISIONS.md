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
