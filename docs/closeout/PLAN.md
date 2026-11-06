# Delivery closeout plan

Assignment: [ASSIGNMENT.md](ASSIGNMENT.md) (verbatim copy of the README at commit `ace2b7f`).
Decisions with UTC timestamps: [DECISIONS.md](DECISIONS.md). Live state: `STATUS.json` → `delivery_closeout`.

This is a reproducibility and reporting closeout of the completed v2 study. Nothing is retrained. The only new
simulator evidence is (a) the Stage 4 repeatability evaluation of existing v2.0.0 checkpoints, (b) Stage 2
negative controls, and (c) Stage 7 verification replays and a two-iteration resume smoke test. None of
these is used to select checkpoints, constants, thresholds or reportable subsets.

## Source roles

| Role | Revision | Used for |
|---|---|---|
| Experiment checkout | tag `experiment-v2` = `1d9d0e23eec346c1b1cb3c0c245a1e772df7bedf` | every simulator command (training replay, evaluation, negative controls, resume smoke, videos) |
| Delivery-tools checkout | the closeout tags on `study/v2-diagnostics` (recorded in `STATUS.json`) | download/integrity, CPU regeneration, analysis, rendering, packaging, verification, and the configs/matrices fed to the experiment checkout |

The simulator source (`src/`, `scripts/eval_matrix.py`, `scripts/evaluate.py`, `scripts/train.py`,
`scripts/run_scripted.py`, `scripts/record_video.py`) is checked to be byte-identical between the two
checkouts before any simulator stage (`scripts/closeout.py check`).

## Stages

| Stage | Work | Output |
|---|---|---|
| 1 | Inventory; v2.0.0 anonymous download + checksums + member re-hash; archive assignment; plan, decisions, status, deliverable manifest, run ledger | `docs/closeout/*`, `results/closeout/deliverables.json`, `results/closeout/run_ledger.jsonl` |
| 2 | `scripts/closeout.py` driver (check, download, regen, sim stages, render, package, verify); two-checkout reproduction; script/CLI/link/asset-name checks; CPU regeneration from downloaded raw records vs archived summaries; analysis lock; simulator negative controls | `docs/closeout/REPRODUCE.md`, `results/closeout/regeneration/`, `results/closeout/negative_controls/` |
| 3 | Wording and provenance corrections in README, report, deck, diagnostics, reproduction notes, release notes | `docs/closeout/ERRATA.md` |
| 4 | Repeatability: 8 controllers × 2,400 final cases × 3 process repeats × batch sizes 900 and 23 (115,200 episodes); config, run manifest and analysis plan committed before collection | `configs/closeout/repeatability.json`, `docs/closeout/REPEATABILITY_PLAN.md`, `report/closeout/repeatability.md`, `results/closeout/repeatability/` |
| 5 | Revised report (Markdown + PDF), deck (PPTX + PDF), ten videos verified, every page rendered and inspected | `report/v2/`, `docs/closeout/VERIFICATION.md` |
| 6 | Release `v2.1.1` with copies of all v2.0.0 assets + new artifacts, indices, inventories, SHA256SUMS | GitHub release |
| 7 | Fresh clone + anonymous download; checksums, inventories, indices; driver error/resume paths; regeneration; predeclared replay (first five cases of each of the 12 conditions); resume smoke (≤ 2 PPO iterations); media and document checks | `docs/closeout/VERIFICATION.md` |

## Compute

Warren LSF cluster, queue `gpu_large_shared` (8× A100-40GB node), one GPU per self-terminating job, as in
v1/v2. CPU-only work on a laptop and the CPU queue. Cluster specifics are passed through environment
variables (see `scripts/cluster/README.md`); no step depends on a private path.
