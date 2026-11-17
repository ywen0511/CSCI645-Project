# Post-V3 maintenance decisions (Stage A)

Times are UTC. Scope: verify the CPU-prepared reproduction repairs on the remote GPU environment and publish a
maintenance release. No V3 physics, checkpoint, frozen suite or published number is changed.

## 2026-11-09 15:01 — environment inventory

dgx047 (8 × A100-SXM4-40GB, driver 580.159.03, Ubuntu 24.04.5, kernel 6.8.0-124), Isaac Sim 6.2.0.0, Isaac Lab
v3.0.0 (package `isaaclab` 28.0.0), Python 3.12.16, torch 2.11.0+cu130, RSL-RL 5.5.1, warp 1.17.0 — identical to
`docs/SETUP_REMOTE.md` and `configs/v2/frozen/pip-freeze.txt`. GitHub push/release rights through the
repository collaborator account were confirmed. No compute was purchased or provisioned; all GPU work used
already-available LSF slots on one node (other users' jobs were never touched).

## 2026-11-09 15:05 — CPU test suite

`CUDA_VISIBLE_DEVICES='' python -m pytest -q` in an isolated Python 3.13.9 venv (torch 2.x CPU, numpy, pytest):
60 passed, 1 skipped. The skip is `tests/test_registration.py` (Isaac Lab not installed in the CPU venv). The
archived-suite integration test did **not** skip: the full history containing `experiment-v3` was fetched.

## 2026-11-09 15:30 — portable Python for the analysis lock

The cluster has no `python3.13`; the analysis lock pins Python 3.13.9. A portable CPython 3.13.9
(python-build-standalone release 20251014, checksum verified against its published SHA256SUMS) was placed on
PATH for the job, so `docs/v3/REPRODUCE.md` sections 1–4 ran verbatim in one shell.

## 2026-11-09 15:32–15:44 — REPRODUCE sections 1–4 (job script extracts the bash blocks of the tooling commit)

Tooling commit `4d7beb30bda29ea0bedd83f6eb48fe63d5b9768d`; fresh public clones and an anonymous download into a
new workspace. All steps exit 0 and the section-4 assertion block passed. Results in `results/post_v3/stage_a/`.

- Archive verification ok; three rebuilt suites byte-identical to the archive (development 312, validation 240,
  final 2,600; SHA-256 recorded).
- Table regeneration: 34 of 35 JSON/CSV files byte-identical; `mechanisms/mechanisms.json` is numerically equal
  (116 regression values differ by at most 8.9e-16 absolute, about one unit in the last place). The node is an
  AMD EPYC 7543; the published tables were generated on a different x86 CPU, and the least-squares fits use
  BLAS. Classified as floating-point rounding, not a mismatch. All 6 regenerated figures are byte-identical.
- 455 replay and 52 reload episodes equal the published terminal outcomes; two-iteration resume 306 → 308,
  10,027,008 → 10,092,544 transitions; the released checkpoint's SHA-256 is unchanged.
- Repeat of the runner: all 13 tasks skipped after content verification; the ledger is byte-identical before
  and after (no simulator launch).

## 2026-11-09 15:50 — record-level audit (`scripts/post_v3_replay_audit.py`)

Beyond the comparator's counts: each entry's case-ID set equals its subset suite exactly, no duplicates, 0
invalid resets, 0 infrastructure errors, source commit = `experiment-v3`, suite hash = subset suite file,
config/controller/checkpoint/observation-error equal to the published records, checkpoint SHA-256 equal to the
release index. First run reported one discrepancy: `geometry_best_constant` records carry their own entry ID,
whereas the published final records of that role carry `geometry_common`, because the two roles are a declared
exact alias (`configs/v3/final_matrices/baseline_aliases.json`). The audit now resolves declared aliases
explicitly (and still requires the replay's own ID to be the replayed role); result 0 discrepancies.

## 2026-11-09 15:35 — cache false-hit demonstration (`scripts/post_v3_cache_demo.py`)

Disposable git fixtures driven through the real runner CLI: repeat skip; edited output bytes, directory member
added/removed, changed checkpoint input and legacy ledger are all refused without a launch; a missing output and
a failed latest attempt (outputs present, rc 3) both run again. 8 of 8 scenarios pass. A first version of the
failed-attempt fixture was wrong (its injected failure was itself skipped as complete); the fixture was fixed to
crash after writing outputs, not the runner.

## 2026-11-09 16:00 — maintenance release layout

`v3.0.1` keeps every v3.0.0 asset byte-identical inside one uncompressed archive
(`v3.0.0-original-assets.tar`), because several original asset names (`SHA256SUMS`, `release_manifest.json`,
`REPRODUCE.md`) are also names of the new release's own indices. Extracting it gives exactly the v3.0.0 bundle,
on which the original verifier runs unchanged. A new packager (`scripts/post_v3_package.py`) and verifier
(`scripts/post_v3_verify_release.py`) were written instead of reusing the V3 packager, whose hard-coded layout
would omit the maintenance evidence. `v3.0.0` is not modified.

## 2026-11-09 16:10 — publishing v3.0.1 (upload failure and recovery)

The first `gh release create` failed while uploading the 461 MB `v3.0.0-original-assets.tar`
(`tls: bad record MAC`); GitHub kept no release. A draft with the ten small assets was then created, but three
further uploads of the large asset from the workstation (gh and curl, with and without a rate limit) failed
the same way after ~49 MB: the workstation's outbound link was corrupting long TLS uploads. The packager was
re-run unchanged from a clean clone of `maintenance-v3.0.1` on the cluster against that machine's own
anonymous v3.0.0 download; the nested archive was byte-identical (SHA-256 `809130f2…862b`), and it was
uploaded from there (the token was passed on standard input, never written to disk). All 11 draft assets were
reconciled by size and SHA-256 against the local bundle before the draft was published. The other small assets
differ between the two builds only in git-archive gzip bytes (git version), so the published set is exactly
the workstation build listed in its `SHA256SUMS`.

## 2026-11-09 16:17 — public verification of v3.0.1

From a new empty directory on the GPU cluster with public clones only (`maintenance-v3.0.1`, `v3.0.0`,
`experiment-v3`) and an anonymous download of all 11 assets: `SHA256SUMS` ok; parent verification ok (788
archive members re-hashed, 30 original assets equal to the manifest and the original `SHA256SUMS`, 457 of 457
checkpoints resolved inside their original archives); original verifier ok on the extracted bundle; 34 of 35
tables identical and 1 equal within rounding; 6 of 6 figures identical; suite rebuild check ok; 65-case
replay (geometry_common) and 13-case reload (combined_robust_ff) from the extracted checkpoints equal the
published records. Record: `results/post_v3/release_verification/`. Stage A is complete.
