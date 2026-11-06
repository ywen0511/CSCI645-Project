# Stage 4 analysis plan: bounded repeatability evaluation

Committed before any Stage 4 result was collected. Design: [`configs/closeout/repeatability.json`](../../configs/closeout/repeatability.json);
task list: [`results/closeout/repeatability/run_manifest.json`](../../results/closeout/repeatability/run_manifest.json);
analysis script: `scripts/closeout_repeatability.py`.

## Status of this evaluation

This is a **retrospective robustness check on the already-used v2 final suite**. It is not a new held-out or
confirmatory experiment, and it trains or tunes nothing. No checkpoint, constant, threshold, case subset or
reportable comparison is selected from these replays. The original v2 numbers stay as published; the
supplementary numbers are reported in separate tables.

## Design (fixed)

- Cases: all 2,400 v2 final cases (`configs/v2/suites/final.jsonl`, SHA-256 `041ca5cf…`), in suite order, with
  their existing IDs, perturbations and evaluator (`eval_matrix.py` at `experiment-v2`).
- Controllers (8): `geometry_1p5cm` (geometry, 1.5 cm alignment bound); `const_geometry_1p5cm` (the same plus the
  already-selected +10 mm x constant); `combined_seed{11,22,33}__selected`; `combined_seed{11,22,33}__final`.
  Checkpoints: the downloaded, checksum-verified v2.0.0 files; SHA-256 values are recorded in the config and
  checked by `eval_matrix.py` in every record.
- Deduplication: none (selected and final files differ in bytes for every seed).
- Process repeats: 3 fresh processes per controller and batch size with process seeds 6454101, 6454102 and
  6454103. Within one repeat every controller uses the same seed and case order.
- Batch sizes (environment layouts): 900 (as in the original v2 evaluation, seed 0) and 23.
- Scheduled: 8 × 2,400 × 3 × 2 = 115,200 episodes, 48 tasks. A short throughput check precedes the full run.
  A failed or incomplete task may be resumed at most twice; every attempt is kept in the run ledger.

## Outcomes per task (controller × repeat × batch size)

Scheduled, recorded, duplicate, missing and invalid-reset counts (`reset_valid == false`); success, drop,
prohibited collision, episode timeout, release timeout and any other terminal reason. Rates use **all
scheduled cases** as the denominator. Missing or invalid cases count as non-successes and are reported; they
are never dropped into a valid-only rate.

## Comparisons

For each batch size, repeat and checkpoint role (selected and final analysed separately):

1. combined − geometry_1p5cm (success, percentage points);
2. combined − const_geometry_1p5cm.

"combined" is the mean over the three training seeds. Interval: the v2 two-level paired bootstrap
(`csci645_handover.v2_analysis.paired`: training seeds resampled within method, one shared draw of case
columns; 10,000 replicates, seed 645). The deterministic controllers are single rows.

Repeat summary per batch size: (a) the range and sign of the difference across the three repeats; (b) a
repeat-averaged estimate in which each case's outcome is first averaged over the three repeats within each
training seed (and within each deterministic controller), followed by the same bootstrap over seeds and
cases. Process repeats are therefore **never treated as independent cases or as new training seeds**, and
the 6 × 2,400 repeated episodes are never pooled as independent observations. The two batch layouts are
separate sensitivity analyses and are not pooled.

Agreement with the archived v2.0.0 record of the same controller and case: terminal reason equal and
success flag equal, as counts out of 2,400 per task. These are two different statistics and are reported
separately.

## Interpretation rule (fixed in advance)

- If the sign of combined − geometry_1p5cm differs between any two repeats or layouts, or the interval of the
  repeat-averaged estimate includes 0 in either layout, the small difference is described as
  **unresolved / sensitive to evaluation layout and process**.
- Otherwise it is described as a stable small disadvantage **under the tested settings only** (this suite,
  these checkpoints, two batch layouts, three processes).
- The comparison with const_geometry_1p5cm is reported independently, whatever the result of the first.
- Training-seed variability is only what three trained seeds provide; repeats do not add trained seeds.

## Outputs

`results/closeout/repeatability/{summary.json, per_task.csv, comparisons.csv, agreement.csv}`,
`report/closeout/repeatability.md`, and `report/closeout/figures/repeatability_*.png`.
