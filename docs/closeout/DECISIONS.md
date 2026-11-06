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
