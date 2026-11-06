# Closeout verification record

Actual checks and outcomes. Paths: `$WORK` = the driver's work folder. "Cluster" = Warren LSF,
A100-SXM4-40GB, driver 580.159.03, Isaac Lab v3.0.0 / Isaac Sim 6.2.0.0 / RSL-RL 5.5.1 / torch 2.11.0+cu130 /
Python 3.12.16 (`pip freeze` identical to `configs/v2/frozen/pip-freeze.txt` in every simulator job).
"Laptop" = Ubuntu, Python 3.13.9 with `configs/closeout/requirements-analysis.txt` (NumPy 2.4.4), Chrome 155,
LibreOffice 7.3.

## A. Before publication (part of release v2.1.0)

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

## B. Published release (fresh clone, anonymous download)

Recorded after publication in a later commit on `study/v2-diagnostics` (the tag `v2.1.0` is not moved).
Pending at the time this file was packaged into the release.
