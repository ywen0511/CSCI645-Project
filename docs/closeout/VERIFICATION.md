# Closeout verification record

Actual checks and outcomes. Paths: `$WORK` = the driver's work folder. "Cluster" = Warren LSF,
A100-SXM4-40GB, driver 580.159.03, Isaac Lab v3.0.0 / Isaac Sim 6.2.0.0 / RSL-RL 5.5.1 / torch 2.11.0+cu130 /
Python 3.12.16 (`pip freeze` identical to `configs/v2/frozen/pip-freeze.txt` in every simulator job).
"Laptop" = Ubuntu, Python 3.13.9 with `configs/closeout/requirements-analysis.txt` (NumPy 2.4.4), Chrome 155,
LibreOffice 7.3.

## A. Before publication (part of release v2.1.1)

| Check | How | Result |
|---|---|---|
| v2.0.0 integrity | anonymous download into an empty folder (laptop and cluster), `sha256sum -c`, `verify_archives.py` | 31 assets; 30/30 checksums; 19 archives, every member re-hashed, 0 mismatches / unlisted / missing |
| Two checkouts | `closeout.py checkout` | experiment checkout clean at `experiment-v2` = `1d9d0e2`; simulator source byte-identical to the tools checkout (`results/closeout/supplementary_source_identity.json`) |
| Scripts, CLI flags, links, asset names | `closeout.py check` | every required script present in its checkout; every `--help` of the CPU tools exits 0; every flag used in the fenced commands of `docs/closeout/REPRODUCE.md`, `docs/v2/REPRODUCE.md` and the README exists in the script; relative links resolve; asset names in current docs exist in a release asset list (`raw-dev.tar.gz` → `raw-development.tar.gz` corrected) |
| CPU unit tests | `python -m unittest discover -s tests` with the locked Isaac Lab Python on a CPU node | 32/32 pass, 0 skipped, at `experiment-v2` and at the delivery-tools commit (`results/closeout/tests/`); with the CPU analysis environment (no torch) 9 run and 23 skip |
| Simulator smoke + negative controls (real PhysX, not mocked) | `closeout.py negative` on the cluster | clean nominal 1/1 success, clean geometry 1/1 success; `no_receiver` 0/20 success (20 drops); `giver_holds` 0/20 (20 episode timeouts); `table_support` 0/20 (20 episode timeouts): independent receiver holding cannot be satisfied without a receiver, without release or with table support (`results/closeout/negative_controls.json`) |
| CPU regeneration of v2 from downloaded raw records | `closeout.py regen` (laptop) | 51/51 archived files of `results/v2/{final/selection,summary,diagnostics,pilot}` regenerated: 30/30 tables/JSON byte-identical (incl. selection, final tables, ablation, residual diagnostics, nondeterminism, constants, pilots), 21/21 figures regenerated with identical image size (PNG bytes depend on the library build); 0 substantive differences (`results/closeout/regeneration/comparison.json`) |
| Stage 4 repeatability | `closeout.py repeatability --shard i/4` (4 jobs) + `analyze` | 48/48 tasks, 115,200/115,200 episodes, 0 missing / duplicates / invalid resets, 1 attempt each (`results/closeout/repeatability/`) |
| Report numbers | `scripts/closeout_check_numbers.py` | 188 numbers in report §5.1, §5.2, §5.5 and the summary match the machine-readable summaries (`results/closeout/number_check.json`) |
| Report and deck rendering | `closeout.py render`; every page rasterised and inspected | report PDF 11 pages, deck 13 slides; one clipped slide title and one overlap on the title slide found and fixed; no missing figures |
| Draft release validated locally | `closeout.py package` then `scripts/closeout_verify.py` on the draft folder | 38 assets (229.9 MB); SHA256SUMS covers all 37 others; manifest consistent; 18 assets byte-identical to v2.0.0; 23 archives, 1,795 members re-hashed, 0 problems; 170 checkpoint entries resolve (1 superseded, disclosed), 9 final runs with untrained/selected/final/resume roles and 11 step checkpoints; 64 run entries resolve; 10 videos + sidecars resolve, decode fully, and have the indexed frame counts; 115,200 repeatability records; PDFs 11/13/12 pages, PPTX 13 slides |
| Leak scan | same verifier, text members of new archives + loose JSON/Markdown | first pass found the build machine's user name in node-local cache paths, cluster node names in `per_task.csv`, and `file://` home paths in the report PDF; redaction and builders fixed; final draft 0 hits (generic `/home/conda/...` conda-forge build path in pip freeze excluded); historical exposures documented in [ERRATA.md](ERRATA.md) |

## B. Published release v2.1.1 (fresh clone, anonymous download)

Release [v2.1.1](https://github.com/ywen0511/CSCI645-Project/releases/tag/v2.1.1), published 2026-11-06 04:35 UTC;
tag `v2.1.1` → `cfa33d7559d631c49ece9e4b8a868c1f320edaf2` (not moved). This section and the records in
[`results/closeout/verification/`](../../results/closeout/verification/) were committed afterwards on
`study/v2-diagnostics`. Every input came from GitHub without credentials (`GH_TOKEN`/`GITHUB_TOKEN` unset),
into empty folders: one on the laptop (CPU) and one on the cluster (GPU). No file from the uploading session
was used.

| Check | How | Result |
|---|---|---|
| Public access | anonymous `curl -L` of `report.pdf`, `deck.pptx`, `SHA256SUMS`, `checkpoints-combined-seed11.tar.gz`, `closeout-repeatability.tar.gz`, `videos.tar.gz`; unauthenticated GitHub API | HTTP 200 for all; 38 assets, 229,886,273 bytes, published, not a draft; downloaded `SHA256SUMS` identical to the packaged one |
| Quickstart, in order | the copy-paste block of [REPRODUCE.md](REPRODUCE.md) (`git clone`, `checkout v2.1.1`, `python3.13 -m venv`, `pip install -r …`, `download`, `checkout`, `check`, `regen`, `analyze --from-release`, `verify`) | every command rc=0 (`quickstart.log`); `python3.13` came from a conda installation put on `PATH` |
| Integrity | `download` stage: 38 assets, `SHA256SUMS` 37/37, `verify_archives.py` re-hash and extraction | OK |
| Inventories and indices | `verify` stage (`closeout_verify.py`) | 23 archives, 1,796 members re-hashed, 0 problems; 170 checkpoint entries resolve with matching hashes (1 superseded, disclosed); 9 final runs each with untrained/selected/final/resume roles and 11 step checkpoints; 64 run entries and 10 videos + sidecars resolve; 115,200 repeatability records; 18 copied assets keep their v2.0.0 hashes; leak scan 0 hits (`download_verify_v2.1.1.json`) |
| Source revisions and scripts | `check` stage on the fresh clone | experiment checkout clean at `experiment-v2` = `1d9d0e2`; simulator source identical; all required scripts present; all documented flags exist; all links and asset names resolve (`check.json`) |
| Regeneration of original v2 results | `regen` | 51/51 files: 30/30 tables/JSON byte-identical, 21/21 figures regenerated with identical image size; 0 substantive differences (`regen.json`) |
| Regeneration of supplementary results | `analyze --from-release` (records from `closeout-repeatability.tar.gz`) | `summary.json`, `per_task.csv`, `comparisons.csv`, `agreement_pairs.csv`, `archived_reference.csv` byte-identical to the committed files (`analyze.json`) |
| Driver error and resume paths (disposable copies) | see `driver_error_paths.log` | re-download: re-hashes 37 assets, then skips; modified asset in a verified download: refused; modified experiment checkout: refused; repeatability matrix changed after freezing: refused before any simulation; package from a dirty tools checkout or into an existing folder: refused; simulator stage without an Isaac Lab Python: refused; `regen` re-run: identical comparison |
| Simulator resume of a task (cluster, disposable copy) | replay records truncated by 25 cases in 3 entries, status removed, `replay` re-run | `eval_matrix.py` reported "35 existing, 25 to run" for exactly those entries and "60 existing, 0 to run" for the others; the agreement summary equals the uninterrupted run (`resume_test_replay_stage.json`) |
| Simulator hash-mismatch refusal (cluster, disposable copy) | one record's `config_hash` replaced, `replay` re-run | the process stopped at the tampered entry with rc=1 (attempt 2 in `tamper_test_ledger.jsonl`); no record rewritten, no status written. The abort text is not in the log because Isaac Lab exits from inside the simulation context |
| Predeclared replay of downloaded checkpoints | `replay` stage, sample frozen in `configs/closeout/verification_replay.json` (first five case IDs of each of the 12 conditions = 60 cases): nominal, geometry 1.5 cm, both constant controls, selected + final of all 9 runs (residual, combined, combined_no_phase × seeds 11/22/33); one process, batch 60, process seed 0 | 22 entries × 60 = 1,320 records; all checkpoint hashes equal the archived ones; no checkpoint file reused for two roles. Agreement with the archived v2.0.0 records (batch 900): terminal reason 1,309/1,320, success flag 1,312/1,320 (two statistics). Deterministic controllers 239/240 terminal reasons (1 `const_nominal` case); learned 1,070/1,080 (all 10 disagreements are residual policies; combined and combined_no_phase 720/720). This is observed agreement on this sample, not a bitwise-reproducibility claim or a population bound (`replay_comparison.json`) |
| Resume smoke (≤ 2 PPO iterations, disposable output) | `resume-smoke` from the downloaded `combined_seed11/checkpoints/latest.pt` | restored iteration 306 / 10,027,008 transitions; ran exactly 2 iterations to 308 / 10,092,544; optimizer state present (Adam step 6,120 → 6,160), 8 normaliser tensors and RNG state saved, all 11 actor tensors updated; saved file reloads identically; the downloaded checkpoint's SHA-256 is unchanged. Not a scientific result (`resume_smoke.json`) |
| Videos | `verify` (decode every frame) + `video-replay` (re-render the committed plan in single-environment processes) | 10/10 MP4 decode with the indexed frame counts; 10/10 sidecars resolve; 10/10 re-rendered replays reproduce the archived evaluation outcome (`video_replay.json`) |
| Documents | `verify` | `report.pdf` 11 pages, `deck.pdf` 13, `report-v1-corrected.pdf` 12; `deck.pptx` opens with 13 slides; report links point to GitHub at tag `v2.1.1` (no local paths) |

Environment of the GPU checks: `pip freeze` identical to the frozen lock; A100-SXM4-40GB, driver 580.159.03
(`gpu_environment.json`).

**Superseded attempt (v2.1.0).** v2.1.0 (published 04:26 UTC) failed this section at its first step. On both
the laptop and the cluster, `closeout.py download --tag v2.1.0` downloaded 38/38 assets anonymously, then
`verify_archives.py` stopped with `KeyError: 'sha256'` on the `source-v2.1.0.tar.gz` inventory rows
(ERRATA C9). No later step of that attempt counts as verification. v2.1.0 stays published unchanged, and its
notes point to v2.1.1.

**Known tool limitation found after tagging:** in the `v2.1.1` driver, `verify --bundle <path>` resolves a
*relative* path against the work folder. The documented form `verify --tag v2.1.1` is not affected, and an
absolute `--bundle` path works. Fixed on the branch after the tag.
