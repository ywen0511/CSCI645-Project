# v3.0.0 — Observation robustness in bimanual handover

Third study on the two-Franka bar handover (Isaac Lab 3.0 / Isaac Sim 6.2, PhysX). v3 corrupts only the bar's
translation measurement (per-episode bias, per-step noise, delay; a synthetic sensor model, not vision and not
sim-to-real) and asks whether noise-trained residual PPO or a five-frame observation history helps a strong
geometric controller. Experiment source: tag `experiment-v3` (`3811f5da`); this release: tag `v3.0.0` on branch
`study/v3-observation-robustness`. Earlier releases (v1.0.0, v2.0.0, v2.1.1) are unchanged.

## Findings (held-out final suite: 200 base cases × 13 conditions = 2,600 paired cases)

- `geometry_common` (unsmoothed estimate plus a kinematic reference from the giver's grasp while the giver holds)
  succeeds on all 2,600 cases. Every selected combined policy (clean- or noise-trained, feed-forward, five-frame
  history, repeated-current control; 18 runs) also succeeds on every case.
- Both primary contrasts on `mixed_id` (history − robust feed-forward; history − `geometry_best_constant`) are
  exactly +0.0 pp with zero-width 95% and 97.5% Bonferroni intervals. This is a ceiling: the suite cannot rank
  these policies, and nothing here shows that history or noise-trained residuals help.
- Without the giver reference, the estimator decides: raw-estimate geometry falls to 0.5% at 2 mm noise and 0% on
  `mixed_id` (release-gate timeouts); EMA filtering fixes noise but not 10 mm bias (67.5%, collisions). Delay up
  to 200 ms has no effect.
- History training is unstable late: at the 10M final checkpoint three of five history runs lose ≥ 22 pp and seed
  55 collapses (residual saturates at the bound, collisions). Validation-based selection avoided this.
- Residual-only history PPO on the nominal script does not beat the script (−1.8 pp [−10.2, +4.4] on `mixed_id`).
- Learned residuals act as near-constant episode-mean offsets (x intercept −2.6 to −0.4 mm) that ignore the
  injected sensor bias; frame-permutation and current-frame-only interventions change no outcome.
- Repeatability: 2,730 of 2,730 reruns (3 process seeds × batch 1/23, 65 cases, 7 entries) reproduce the original
  terminal outcome.

Full report: `report.md` / `report.pdf`; slides: `slides.pptx` / `slides.pdf` with `speaker_notes.md`.
All numbers trace to generated files via `results/v3/number_audit.json` (in `analysis.tar.gz` and the branch).

## Assets

| asset | content |
|---|---|
| `source-experiment-v3.tar.gz`, `source-v3.0.0.tar.gz` | git archives of the experiment and delivery commits |
| `checkpoints-formal-<family>.tar.gz` (5) | every checkpoint of the 23 formal runs (step 0, ten periodic saves, final, latest with optimizer/normalizer/RNG/counters) plus run metadata and PPO logs |
| `checkpoints-pilot-smoke.tar.gz` | 8 pilot runs, 5 smoke runs and their resume runs, and the superseded first attempt's runs |
| `raw-development`, `raw-validation`, `raw-final`, `raw-extras`, `raw-acceptance` `.tar.gz` | every evaluation record and trace (development 85 entries, validation 138 × 240, final 50 × 2,600, zero-policy, interventions, repeatability, 6-case traces, acceptance, pilot evaluation, superseded attempt) |
| `logs.tar.gz` | per-task logs, job ledgers and scheduler logs |
| `analysis.tar.gz` | `results/v3`, `configs/v3` (frozen protocol, suites, matrices, indices), report sources |
| `videos.tar.gz`, `videos.json` | 8 clips + montage with sidecars (frozen selection rule) |
| `report.*`, `slides.*`, `speaker_notes.md`, `REPRODUCE.md`, `VERIFICATION.md`, `RELEASE_NOTES.md` | documents |
| `checkpoints.json`, `run_index.json`, `archive_inventories.json`, `release_manifest.json`, `SHA256SUMS` | indices and integrity |

`SHA256SUMS` covers every asset except itself; `release_manifest.json` lists every other asset and maps every
logical run, checkpoint, final-matrix entry and validation evaluation to its asset, member, size, SHA-256 and
lineage; `archive_inventories.json` lists every archive member with size and SHA-256. Text members are redacted
(private path prefixes → `<RUNS>`, `<WORK>`, …; host names → `<cluster-node>`); scientific content is unchanged.
Checkpoints are archived in full; identical bytes are listed in `checkpoints.json` (`identical_bytes_as`).

## Not performed

The optional physical-transfer extension (mass/friction/size changes) was not performed: the bar's spawn
geometry, mass and material are module constants, and validated spawn overrides were not implemented before the
freeze. Nothing about physical transfer is claimed.

## Reproduction and verification

`REPRODUCE.md` (clean-clone setup, download and checks, CPU regeneration of every table, GPU replay, full
evaluation, resume, video replay). `VERIFICATION.md` records the checks run on this release; the fresh-download
verification after publication is in `docs/v3/VERIFICATION.md` on the branch.

## AI assistance

Implementation, experiments, analysis, report, slides and videos were produced by an AI coding agent (Anthropic
Claude via Claude Code) working from `V3_EXECUTION.md` on the owner's behalf; decisions are logged in
`docs/v3/DECISIONS.md`.
