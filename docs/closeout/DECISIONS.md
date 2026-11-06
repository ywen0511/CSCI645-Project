# Delivery closeout decision log

UTC timestamps from `date -u`. Evidence paths are repository-relative unless marked as work-directory paths
(`$WORK` = the driver's `--work` folder). The v1 log (`docs/DECISIONS.md`) and the v2 log
(`docs/v2/DECISIONS.md`) are historical and unchanged.

### 2026-11-06 02:10 UTC — Start of the closeout

- Assignment: README of `study/v2-diagnostics` at `ace2b7f`, archived verbatim as
  [ASSIGNMENT.md](ASSIGNMENT.md) (SHA-256 `a4fb7d47…`, identical to the README). `docs/v2/ASSIGNMENT.md` and the
  original proposal are unchanged.
- Inventory: branch `study/v2-diagnostics` at `ace2b7f` (only change since `3a8fe0a`: the README). Tags
  `experiment-v1` → `7a64505`, `v1.0.0` → `8287646`, `experiment-v2` → `1d9d0e2`, `v2.0.0` → `86b193a`. Releases
  v1.0.0 and v2.0.0 exist; `v2.1.0` is unused. The repository is public; GitHub write access is available.
- v2.0.0 downloaded anonymously (HTTPS, no token) into an empty folder: 31 assets; `sha256sum -c SHA256SUMS`
  30/30 OK; `verify_archives.py` re-hashed every member of the 19 archives: 0 mismatches, 0 unlisted, 0 missing.
- Compute: Warren LSF cluster, queue `gpu_large_shared`; the 8× A100-40GB node used for v1/v2 has 4 idle GPUs
  (driver 580.159.03). The isolated Isaac Lab environment of v1/v2 (Isaac Lab v3.0.0, Isaac Sim 6.2.0.0,
  RSL-RL 5.5.1, Python 3.12, PyTorch 2.11/CUDA 13) is still installed; it is reused unchanged (no upgrades).
- Script audit: `REPRODUCE.md` (v2) invokes `build_report_v2.py`, `build_deck_v2.py`, `package_v2.py` and
  `verify_v2_release.py`, which do not exist at `experiment-v2`, and `v2_nondeterminism.py`, which exists only
  after `v2.0.0`. Fix: two checkouts with fixed roles (experiment `experiment-v2`; delivery tools = closeout tags),
  and a driver (`scripts/closeout.py`) that checks script presence per checkout before running.

### 2026-11-06 02:15 UTC — Stage 4 design frozen before collection

- Controllers: `geometry_1p5cm`, `const_geometry_1p5cm` (+10 mm x), `combined_seed{11,22,33}__{selected,final}`,
  copied from `configs/v2/matrices/final/`. Checkpoint SHA-256 from the v2.0.0 index; they equal the hashes in
  the archived final records.
- Deduplication: none. Seeds 22 and 33 selected `step_010027008`, the last periodic checkpoint, but `final.pt`
  is a different file (different bytes), so under the rule (identical bytes + settings + case order) all 8
  entries are evaluated: 8 × 2,400 × 3 × 2 = **115,200 episodes**, 48 tasks.
- Task unit: one fresh simulator process per (batch size, repeat, controller), process seeds
  6454101/6454102/6454103, batch sizes 900 and 23. `seed` and `num_envs` are excluded from the configuration
  hash (`runtime.py`), so records stay hash-compatible with the archived ones.
- Retry policy: at most 3 attempts per task (1 + 2 resumes), all recorded.
- Predeclared Stage 7 replay sample frozen at the same time: first five case IDs of each condition (60 cases),
  22 entries (nominal, geometry 1.5 cm, both constants, selected + final of all 9 runs).
- Analysis plan: [REPEATABILITY_PLAN.md](REPEATABILITY_PLAN.md).

### 2026-11-06 02:40 UTC — Throughput check and freeze of the supplementary-evaluation source

- Throughput check (not part of the results; `$WORK/sim/throughput`): `combined_seed11__final` on the 200 clean
  cases, process seed 6454101, one A100-40GB: batch 900 → 11 s simulation, ~79 s per process including start-up;
  batch 23 → 79 s simulation (9 chunks), ~98 s per process. Estimate for the full matrix: 24 batch-23 tasks ×
  ~16 min + 24 batch-900 tasks × ~2 min ≈ 7 GPU-hours, ≈ 2 h on 4 GPUs. Jobs: 4 self-terminating 1-GPU LSF jobs
  (`--shard i/4`), wall limit 4 h each; no other retries beyond the frozen policy.
- CPU regeneration from the downloaded v2.0.0 raw records with the pinned analysis environment
  (`configs/closeout/requirements-analysis.txt`, NumPy 2.4.4): 51/51 archived files of `results/v2/{final/selection,
  summary,diagnostics,pilot}` regenerated; 30/30 tables/JSON byte-identical, 21/21 figures regenerated with
  identical image sizes (PNG bytes depend on the library build). The 12 trace figures needed the
  `v2_plot_traces.py` commands of the v2 study, which were not in any guide; they are now in the driver's
  `regen` stage.
- Supplementary-evaluation source: tag `closeout-eval-v1`. Simulator code (`src/`, eval/train/scripted/video
  scripts), frozen protocol, final suite and final matrices have identical git object IDs at `experiment-v2` and
  at the tag (`results/closeout/supplementary_source_identity.json`); there are no behavioural or
  non-behavioural changes. Simulation still runs from the clean `experiment-v2` checkout.

### 2026-11-06 02:48 UTC — Correction to the 02:40 entry

- The 02:40 entry (inside tag `closeout-eval-v1`) says the final matrices have identical object IDs at
  `experiment-v2`. That is wrong for one folder: `configs/v2/matrices/final` gained the 9 learned-run matrices and
  `final_manifest.json` in `38a12ec`, after `experiment-v2`, because they encode the frozen checkpoint selection.
  The deterministic matrices (`final_det_*`, `final_manifest_det.json`), `src/`, all simulator scripts, the frozen
  protocol and the final suite are identical. The record at the tag already showed `"all_identical": false` with
  the `git diff --stat`; it now also classifies each path. The tag is not moved.
- Stage 4 launched: 4 shards (LSF jobs 8048991, 8048995–8048997), tools checkout at `closeout-eval-v1`,
  experiment checkout at `experiment-v2`. Negative controls queued (job 8048999).
