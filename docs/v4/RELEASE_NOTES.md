# v4.0.0 — Uncertain giver grasp in bimanual handover

Fourth study on the two-Franka bar handover (Isaac Lab 3.0 / Isaac Sim 6.2, PhysX, parallel-jaw grippers, bounded XYZ
residual PPO). V4 makes the bar's initial translation inside the giver's grasp a physical, per-episode unknown
(x ∈ [−7, +15] mm along the bar, z ∈ ±15 mm) and measures where V3's fixed-transform grasp reference fails and whether
calibration, filtering, short observation history or residual PPO help. Simulator source of every formal run: tag
`experiment-v4` (`aac4d98`); this release: tag `v4.0.0` on branch `study/v4-grasp-uncertainty`. Earlier releases
(v1.0.0, v2.0.0, v2.1.1, v3.0.0, v3.0.1) are unchanged.

## Findings (final suite: 12 conditions × 200 paired base cases = 2,400 cases; 132,000 logical / 129,600 executed episodes)

- The historical fixed-transform reference fails beyond about +5 mm toward the receiver: 39.5% at +10 mm,
  5.5% at +15 mm, 69.5% on `mixed_id` (receiver collides with the bar end).
- A 0.5 s calibration from the same noisy measurements fixes most of it: 94.5% at +15 mm,
  98.5% on `mixed_id` (+29.0 [+23.0, +35.5] pp vs fixed). It inherits sensor bias; EMA
  geometry is close in distribution (99.0%) and worse under heavier corruption.
- Primary contrasts (mixed_id, selected checkpoints): robust history − robust FF +0.6 [+0.0, +2.0] pp;
  robust history − best constant geometry +1.5 [+0.0, +3.5] pp (Bonferroni 97.5%
  [+0.0, +3.5]). Both touch zero: no improvement established, no equivalence claimed.
- Learned residuals are fragile outside their training support: at x = −7 mm robust history reaches 65.2%
  versus 96.5% for its calibrated parent; final (10M) history checkpoints degrade; residual-only PPO on the
  nominal trajectory does not beat it (−3.2 [−10.5, +2.9] pp on `mixed_id`) and collapses by its final checkpoint.
- Mechanisms: a constant fitted on development records matches every selected history policy on a 60-case subset;
  reversing or removing frame order changes few outcomes. Repeatability: 2,160/2,160 reruns reproduce the outcome.
- Invalid resets: 380 records, all at the −7 mm palm limit (bar touches the giver hand while settling), count as failures for
  every method.

Full report: `report.md` / `report.pdf`; slides: `slides.pptx` / `slides.pdf` with `speaker_notes.md`. Every number traces
to generated files via `results/v4/number_audit.json` (in `analysis.tar.gz` and the branch).

## Assets

| asset | content |
|---|---|
| `source-experiment-v4.tar.gz`, `source-v4.0.0.tar.gz` | git archives of the experiment and delivery commits |
| `checkpoints-formal-<profile>.tar.gz` (5) | every checkpoint of the 25 formal runs (step 0, ten periodic, final, latest with optimizer/normalizer/RNG/counters) + run metadata, training logs, TensorBoard |
| `checkpoints-pilot-smoke.tar.gz` | four completed pilots, the killed packed pilot attempt, five smoke runs and their resumes |
| `raw-development`, `raw-validation`, `raw-final`, `raw-extras`, `raw-acceptance` `.tar.gz` | every evaluation record and trace (probe and two development rounds, 150 × 240 validation, 54 × 2,400 final, mechanisms, repeatability, six-case traces, acceptance passes incl. the failed first table-support control, pilot evaluations) |
| `logs.tar.gz` | per-task logs, task ledgers, runner logs, LSF job logs (incl. failed/killed jobs) |
| `analysis.tar.gz` | `results/v4`, `configs/v4` (freeze, suites, matrices, index), report sources |
| `videos.tar.gz`, `videos.json` | 10 clips + montage with sidecars (frozen rule) |
| `report.*`, `slides.*`, `speaker_notes.md`, `REPRODUCE.md`, `VERIFICATION.md`, `RELEASE_NOTES.md` | documents |
| `checkpoints.json`, `run_index.json`, `archive_inventories.json`, `release_manifest.json`, `SHA256SUMS` | indices and integrity |

`SHA256SUMS` covers every asset except itself; `release_manifest.json` lists every other asset and maps every logical
run, checkpoint, final-matrix entry and validation evaluation to its asset, member, size, SHA-256 and lineage;
`checkpoints.json` gives run/profile/seed/transitions/role/source/config hash per checkpoint. Text members are redacted
(private path prefixes → placeholders; host names → `<cluster-node>`); scientific content is unchanged.

## Not performed

The optional dynamic-slip experiment was not performed; nothing about slip robustness is claimed.

## Reproduction and verification

`REPRODUCE.md`: public clones, anonymous download, checksum and inventory verification, CPU regeneration of every table
and figure, a complete 60-case replay, a reload of every architecture and a two-iteration resume. The public-download
verification of this release is recorded in `docs/v4/VERIFICATION.md` on the branch after publication.

## AI assistance

Implementation, experiments, analysis, report, slides and videos were produced by an AI coding agent (Anthropic Claude
via Claude Code) working from `POST_V3_EXECUTION.md` and `V4_REMAINING.md` on the owner's behalf; decisions are logged
in `docs/v4/DECISIONS.md`.
