# Deliverables and publication contract

## Required delivery

Publish the implemented source and all evidence needed to inspect, replay, and resume the reported experiments. Keep ordinary Git history small; store large binary outputs in GitHub Release assets. A release of this initial specification is not a final experimental release.

| Category | Required contents |
|---|---|
| Source | External task package, controllers, PPO integration, evaluator, analytics, tests, exact setup/reproduction commands, dependency lock, original proposal |
| Configuration | Frozen resolved scene/control/reward/observation/training configs, case suites and hashes, experiment source commit/tag, analysis commit, environment inventory |
| Checkpoints | Selected and final checkpoints for all nine trained runs; resume state and normalization included or separately indexed; periodic checkpoint retention ledger |
| Raw evidence | Complete episode records for all methods/conditions/seeds, reset/error records, validation history, training scalar logs, run ledger, representative traces |
| Analysis | Count reconciliation, per-seed/aggregate metrics, uncertainty calculations, learning curves, failure breakdown, figure source data |
| Report | Final English Markdown and PDF; no invented course formatting requirements; actual AI/software-use disclosure and verified references |
| Videos | Clean baseline, method comparisons, observed representative failures, and provenance index |
| Reproduction | Tested clean-clone setup, download/checksum, evaluate/replay, regenerate-figures, and training-resume instructions |
| Release metadata | Asset manifest, SHA256SUMS, checkpoint/video/run indexes, release notes, verification record, accessible GitHub URLs |

## Recommended assets

- `report.pdf` and `report.md`.
- `results.tar.gz`: all episode data, validation records, summaries, plots, analysis inputs, and representative traces.
- `logs.tar.gz`: all final training logs, run ledgers, preflight/acceptance records, and pilot summary/logs.
- `configs.tar.gz`: frozen configs, explicit suites, dependency locks, environment inventory, and reproducibility instructions.
- One checkpoint archive per method/seed, e.g. `checkpoints-combined-seed11.tar.gz`, containing selected/final/resume checkpoints, normalization, and metadata. Identical selected/final weights may be stored once with explicit aliases in the index.
- `videos.tar.gz` plus `videos.json`; optionally upload a short showcase MP4 separately.
- `checkpoints.json`, `runs.json`, `manifest.json`, `SHA256SUMS`, and `REPRODUCE.md`.

Retain all final-run periodic checkpoints when practical. If there is a documented storage limit, retain selected, final, latest resumable, and every checkpoint used by a published evaluation/figure/video; publish the retention ledger. Do not delete needed checkpoints before verifying the remote copies. No fabricated or randomly initialized weights may be advertised as trained.

Use manageable per-asset sizes, for example below 1 GiB, and check GitHub's current limits before upload. Split large archives with documented reconstruction instructions and per-part hashes if needed. Keep uncompressed member inventories and content hashes in addition to archive hashes where feasible. Exclude credentials, remote home paths, caches, virtual environments, and restricted simulator binaries. Preserve required upstream licenses/notices for reused code.

## Manifest format

Create `manifest.json` at the release bundle root with:

```json
{
  "schema_version": 1,
  "status": "complete",
  "experiment_source_commit": "40-character actual Git commit SHA",
  "analysis_commit": "40-character actual Git commit SHA",
  "protocol_sha256": "64-character actual frozen protocol SHA-256",
  "release_tag": "v1.0.0",
  "artifacts": [
    {
      "path": "report.pdf",
      "kind": "report",
      "size_bytes": 123,
      "sha256": "64-character actual file SHA-256"
    }
  ]
}
```

This snippet is illustrative, not a valid completed manifest. Required kinds are `report`, `results`, `logs`, `configs`, `checkpoints`, `videos`, `reproduction`, and `index`. Give every payload file its own entry; do not include `manifest.json` or `SHA256SUMS` themselves in the artifact list. Generate `SHA256SUMS` for the manifest and every payload file, avoiding recursive self-hashing. Use relative POSIX paths with no parent traversal. For checkpoint archives include `method` and integer `seed`; cover all method/seed pairs from the frozen protocol. Checkpoint index entries identify selected/final/resume roles, archive member names, individual hashes, training transitions, normalization, validation score, observation schema, and replay command.

Run:

```bash
python3 scripts/verify_release.py --bundle release_assets --protocol configs/frozen/protocol.json
```

The provided utility checks the manifest, local hashes/sizes, checksum list, and checkpoint method/seed coverage. It does **not** validate archive semantics, policy quality, experiment completeness, or online availability. The remote agent must additionally inspect archive members, reconcile run/episode counts, verify selected/final roles and replay, check report numbers, and perform the fresh-download checks below. Never treat a hash check as evidence that the research succeeded.

## Publication procedure

1. Complete the acceptance gates and final report. Commit source/configs/small summaries. Identify the experiment commit separately from later analysis/reporting commits.
2. Create an immutable experiment tag, such as `experiment-v1`, at the exact code used for final runs. Use a new tag if already occupied by other content; never move a published tag.
3. Package assets and generate indexes/checksums. Validate locally, including archive contents and checkpoint replay. Create final release notes with actual measured results and limitations.
4. Create a draft release at a specific committed delivery revision, upload every required asset, and verify inventory and sizes. GitHub CLI examples, if installed and authenticated:

   ```bash
   gh release create v1.0.0 --repo ywen0511/CSCI645-Project --target COMMIT_SHA --draft --title "CSCI 645 final experiments" --notes-file release-notes.md
   gh release upload v1.0.0 release_assets/* --repo ywen0511/CSCI645-Project
   ```

   Replace the documented placeholders with actual values. Do not use `--clobber` to overwrite existing published assets. Use equivalent authorized API tooling if the CLI is unavailable. Use a new version if a final release already exists.
5. Download all assets into an empty directory from GitHub, validate hashes, inspect archives, and load at least one selected checkpoint from **each learned method**, with its normalization and config, in a fresh process. Run at least ten predefined replay cases per loaded policy. Verify the report and videos open, and analysis regenerates from downloaded raw records.
6. Publish the draft only after these checks. Verify public release/asset URLs after publication. Add release URLs and verification evidence to the repository, update `STATUS.json`, and push the final delivery-index commit. If the release tag precedes this URL-only commit, document both; never imply they are the same commit.

GitHub Actions build logs or expiring artifacts alone do not satisfy persistence. A README link to a remote machine is insufficient. Upload checkpoints and raw evidence even when the combined method underperforms.

## Final report contents

Use a readable academic structure: abstract; motivation and related work; task and physical setup; nominal/geometry/residual/composition equations; observations/rewards/release conditions; experimental protocol and resource budget; results; ablation; failure analysis; limitations; conclusion; reproducibility; references and disclosures. Include all four primary methods and the phase ablation, fixed-orientation limitation, actual training seeds/budgets, validation selection, denominators, uncertainty, and infrastructure exclusions.

Avoid copying the proposal's historical disclosure as a description of completed work. State actual software reuse and AI assistance. Verify reference metadata from primary sources, including the venue of the handover paper, rather than copying an unverified bibliography entry.

## Final completion checklist

- [ ] Every required method/seed/condition has reconciled results or is explicitly reported incomplete.
- [ ] All reported figures and metrics regenerate from archived raw data.
- [ ] All nine runs have selected/final/resume checkpoint coverage and metadata.
- [ ] All mandatory assets are uploaded, downloadable, nonempty, and hash-verified.
- [ ] A clean checkout can install the task and run documented baseline/policy replay.
- [ ] Separate-process replay works using downloaded artifacts for every learned method.
- [ ] Report PDF and representative videos have been visually checked.
- [ ] Final source/tag/release URLs are correct and completion status is truthful.
