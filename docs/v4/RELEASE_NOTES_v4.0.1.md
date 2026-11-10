# v4.0.1 — delivery patch for the V4 uncertain-grasp study

**No new results and no changed data.** Tag `v4.0.0` lacked the GPU verification stage that `REPRODUCE.md`
section 3 runs (`results/v4/jobs/verification.json`, its replay/reload matrices and the 12-case reload suite): the
stage was implemented in `scripts/v4_manifests.py` but never generated before tagging. The public-download
verification of v4.0.0 found this. Published tags and assets are immutable, so this patch adds a new delivery tag.

- Use tag `v4.0.1` for the tooling; download the data from release **v4.0.0** (all checkpoints, raw records, logs,
  videos, report and slides), which is unchanged. `release_manifest.json` here lists every v4.0.0 asset with size and
  SHA-256.
- Simulator source of every formal run is still `experiment-v4` (`aac4d98`).
- Changes from v4.0.0: the generated verification stage, REPRODUCE now clones `v4.0.1` and dry-runs every task except
  the dependent resume inspection, this patch packager, and the decision-log entry describing the gap.

Assets: `source-v4.0.1.tar.gz`, `REPRODUCE.md`, `VERIFICATION.md`, `RELEASE_NOTES.md`, `release_manifest.json`,
`SHA256SUMS`.
