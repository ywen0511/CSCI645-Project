# v2 follow-up study — plan

Branch `study/v2-diagnostics` (from `impl/handover` at `a3bb983`). The follow-up assignment is the
[README](../../README.md) of that commit. v1 files, tags (`experiment-v1`, `v1.0.0`) and assets stay frozen.

## Platform (unchanged from v1, verified in Stage 0)

Isaac Lab v3.0.0, Isaac Sim 6.2.0.0, `isaacsim_physx` backend, RSL-RL 5.5.1, PyTorch 2.11 (cu130), Python 3.12,
in the existing isolated conda environment on the shared filer (`envs/csci645proj`). No package upgrades.
Compute: the single 8x A100-40GB node `dgx047` (LSF queue `gpu_large_shared`); every GPU job is a
self-terminating 1-GPU batch job with a wall-clock limit. CPU work (downloads, analysis, packaging)
uses the CPU queue. No paid resources.

## Stage order and outputs

| Stage | Work | Main outputs |
|---|---|---|
| 0 | Preflight; download + verify v1.0.0; smoke and negative controls | `docs/v2/PLAN.md`, `STATUS.json`, `docs/v2/DECISIONS.md`, `results/v2/stage0/` |
| 1 | Audit v1 (counts, regeneration, replay sample, reward/record order, success logic) | `docs/v2/AUDIT.md`, `docs/v2/V1_ERRATA.md`, `results/v2/audit/` |
| 2 | Residual diagnostics on the v2 development suite (zero / init / trained / constant controls, traces) | `configs/v2/diagnostics.json`, `configs/v2/suites/development.jsonl`, `report/v2/diagnostics.md`, `results/v2/diagnostics/` |
| 3 | Geometry component ablations (A/H/G) and alignment-bound sweep (development) | `report/v2/geometry_ablation.md`, `results/v2/geometry/` |
| 4 | v2 protocol design, feasibility checks, bounded pilots, freeze, tag `experiment-v2` | `docs/v2/PROTOCOL.md`, `configs/v2/protocol.json`, suites, `results/v2/pilot/` |
| 5 | 9 final runs; validation of 5 trained candidates; final evaluation matrix; analysis | `results/v2/final/`, `results/v2/summary/` |
| 6 | Report + deck, >= 10 videos, packaging, release `v2.0.0`, fresh-download verification | `report/v2/`, `docs/v2/REPRODUCE.md`, `docs/v2/RELEASE_VERIFICATION.md` |

## Compute estimate (from measured v1 throughput)

- Training: ~10,000 environment transitions/s on one A100 at 1,024 envs (v1 measurement). Budget 105M
  transitions (15M pilot + 9 x 10M final) is about 3 GPU-hours; final runs execute as parallel 1-GPU jobs.
- Evaluation: 450 cases take 10-16 s of simulation after ~1-2 min of start-up. Development diagnostics and
  ablations (~60 controller configurations x 450 cases) are well under 1 GPU-hour. The final matrix
  (~40 deduplicated configurations x 1,800-2,400 cases) is estimated at 2-4 GPU-hours.
- Totals: roughly 8-12 GPU-hours including smoke tests, replays and videos, well within the node.

## Budgets (fixed by the assignment)

- Pilot training: at most 15M aggregate environment transitions (including smoke training); seeds 101/102.
- Final training: residual, combined, combined_no_phase x seeds 11/22/33, 10M requested transitions each,
  rounded up to whole rollouts.
- Suites: development seed 6453028 (50 cases per v1 condition = 450), validation seed 6453027 (400 cases),
  final seed 6453026 (9 x 200 core + optional 3 x 200 extrapolation at +/-3 cm).

## Diagnostic protocol (summary; exact definitions in `configs/v2/diagnostics.json`)

- Controls on identical development cases: nominal; geometry+zero; geometry + archived combined step-0
  (seeds 11/22/33); geometry + archived combined final; geometry+constant and nominal+constant (x-offset grid
  -5..+5 mm, 1 mm steps, y=z=0, selected on development only by success, fewer collision episodes,
  smaller |offset|, ascending signed offset); archived residual step-0 and final.
- Constant offsets enter the task exactly where the learned residual does: `p_candidate = p_nominal + r`
  with `r` clipped to the same 2 cm per-axis bound, during scored steps only, same control rate.
- Geometry ablations: independent flags A (alignment), H (shared-holding anchor), G (release gate); all 8
  combinations; full A+H+G must reproduce v1 geometry. Alignment bounds 0.005/0.010/0.015/0.020 m.
- Deterministic inference with frozen normalization; traces for predeclared case IDs.

## Output locations

- Git: source, configs, suites, small summaries and figures, docs, report sources.
- Cluster filer (private working area): `kztrgg/runs/csci645-project/v2/{v1_download,stage0,audit,dev,pilot,final,videos,release_assets}`.
- Public: GitHub Release `v2.0.0` (raw records, logs, all checkpoints, videos, report, deck, indices).
