# v3.0.1 — V3 reproduction maintenance release

**No new scientific result.** This release repairs and re-verifies how the published V3 study
(observation robustness in bimanual handover, release `v3.0.0`) is reproduced. Physics, checkpoints, frozen
suites and every published number are unchanged; `v3.0.0` itself is untouched.

Provenance

- Simulator source (unchanged): tag `experiment-v3` = `3811f5da5ef55638f95f7306e449609877f546df`
- Original delivery: tag `v3.0.0` = `ebfa328b17103c32ae19c13f0a6408ebc55a6459`
- Maintenance tooling: tag `maintenance-v3.0.1` (this release's tag `v3.0.1` points to the same commit); its
  SHA is recorded in `release_manifest.json`

What changed (see `MAINTENANCE.md`)

- Reproduction instructions use separate absolute tooling / delivery / experiment checkouts and the
  placeholder-aware runner; the 65-case replay is described as what it is.
- The task runner fingerprints output contents and directory membership, hashes matrix/checkpoint
  dependencies, records resolved execution context and trusts only a successful latest attempt.
- A non-mutating rebuilder reconstructs the three archived suites from the immutable generator.

Remote acceptance on the GPU cluster (2026-11-09; `results/post_v3/stage_a/` in `maintenance-evidence.tar.gz`)

- `docs/v3/REPRODUCE.md` sections 1–4 executed verbatim from fresh public clones and an anonymous download:
  archive verification ok; three rebuilt suites byte-identical; 34 of 35 regenerated tables byte-identical and
  one numerically equal (≤ 8.9e-16 rounding in regression fits on a different CPU); 6 of 6 figures identical;
  455 replay and 52 reload episodes equal the published outcomes; two-iteration resume ok; released checkpoint
  unchanged. Repeating the runner skipped all 13 tasks with no launch.
- A record-level audit (case-ID sets, uniqueness, resets, source/suite/config/checkpoint hashes, outcomes)
  found 0 discrepancies.
- Disposable-fixture demonstrations: edited outputs, directory changes, changed checkpoints and legacy ledgers
  cannot produce a cache hit; missing outputs and a failed latest attempt re-run (8 of 8).
- CPU tests: 60 passed, 1 skipped (simulator import test).

Assets

| asset | content |
|---|---|
| `v3.0.0-original-assets.tar` | all 30 v3.0.0 assets, byte-identical, at the archive root (every checkpoint, raw record, video, report and index) |
| `source-maintenance-v3.0.1.tar.gz` | source at the maintenance tag |
| `maintenance-evidence.tar.gz` | CPU and GPU acceptance evidence, decision log, maintenance scripts |
| `MAINTENANCE.md`, `REPRODUCE.md`, `MAINTENANCE_RELEASE_NOTES.md`, `POST_V3_STATUS.json` | documents and status |
| `checkpoint_locations.json` | every v3.0.0 checkpoint → this release's nested archive → original archive → member, with SHA-256 |
| `archive_inventories.json`, `release_manifest.json`, `SHA256SUMS` | member inventories, provenance/layout manifest, checksums (no self-hash) |

Verify: `python3 -I scripts/post_v3_verify_release.py --bundle <download> --original-out <empty dir>
--output verify.json`, then follow `REPRODUCE.md` section 2 with `--bundle <that dir>`.

AI assistance: the maintenance verification and packaging were carried out by an AI coding agent (Anthropic
Claude via Claude Code) working from `POST_V3_EXECUTION.md` on the owner's behalf.
