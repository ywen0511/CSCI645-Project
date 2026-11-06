# v2 release verification record

Release: [v2.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v2.0.0), published 2026-11-04 07:55 UTC
(draft assembled and validated locally first). Release tag `v2.0.0` → commit `86b193a` (analysis, report,
deck, packaging). Experiment source: tag `experiment-v2` → `1d9d0e2` (frozen protocol, SHA-256 `bd79ae51…`).
This record and the final STATUS/README update were added in a later delivery commit on
`study/v2-diagnostics`; they are not part of the tagged release commit. v1.0.0 and `experiment-v1` are unchanged.

Environment: laptop (Ubuntu, Python 3.13 with NumPy 2.4.4) for CPU checks; cluster node with 8× A100-40GB,
Isaac Lab v3.0.0 / Isaac Sim 6.2.0.0 / PhysX for GPU replay; nothing from the uploading session was used to
obtain the assets (anonymous HTTPS downloads).

| Check | Command (from a fresh directory) | Result |
|---|---|---|
| Local validation before publishing | `scripts/verify_v2_release.py --bundle <release_dir>`; leak scan of every text member, PDF, PPTX and checkpoint | OK; 0 private paths, user names or internal host names (one generic conda build path in the pip lock) |
| Fresh anonymous download | `git clone …; git checkout v2.0.0; python3 -I scripts/download_release.py --tag v2.0.0 --output dl` | 31 assets, 189.3 MB, sizes equal the GitHub metadata |
| Checksums | `cd dl && sha256sum -c SHA256SUMS` | 30/30 OK (all assets except SHA256SUMS itself) |
| Archive members | `scripts/verify_archives.py --bundle dl --extract x` | 19 archives, 996 members re-hashed, 0 mismatches / unlisted / missing |
| Index resolution and counts | `scripts/verify_v2_release.py --bundle dl` | manifest 29 assets OK; 170 checkpoint-index entries resolve with matching hashes (1 marked superseded: the smoke run's first `final.pt`, overwritten by its resume test); all 9 final runs have untrained/selected/final/resume roles and 11 periodic checkpoints; 10 videos resolve; final records 117,600 / 117,600 expected, no duplicates; runs: 9 final + 4 pilot/smoke |
| Regenerate tables from downloaded raw records | `v2_select.py`, `v2_analyze_final.py`, `v2_analyze_dev.py --n-boot 4000`, `v2_select_constants.py`, `v2_analyze_pilots.py`, `v2_nondeterminism.py` on the extracted archives, clean clone at `v2.0.0` | byte-identical: final summary 10/10 files, selection 10/10, development diagnostics 5/5, constants 1/1, pilots 3/3, nondeterminism 1/1 (`results/v2/verification/regeneration.json`). With a different NumPy build (2.5.4) two files differ only in the last digit of `np.polyfit` slopes |
| Clean-clone deterministic episode | fresh `git clone` on the cluster, `experiment-v2`, `run_scripted.py --method geometry --set align_max=0.015 --episodes 1` | success (completion 4.85 s) |
| Replay of downloaded checkpoints in new processes | `eval_matrix.py` with the downloaded checkpoints, predeclared sample of 23 final cases (first 8 where combined seeds disagree, first 8 where residual seeds disagree, first 4 geometry failures, 3 easy cases), batch size 23 vs 900 in the original evaluation: nominal, geometry 1.5 cm, both constant controls, and the selected and final checkpoint of all 9 runs (every method and seed) | 506 records matched: terminal reason equal in **487/506 (96.2%)**, success equal in 492/506. Deterministic controllers 92/92; easy cases 66/66; all 19 disagreements are learned policies on boundary cases (19/360 = 5.3%), 14 change success. Completion times identical on all 313 matched successes. `results/v2/verification/release_replay_comparison.json`. Batched GPU PhysX is not bitwise reproducible across batch layouts; the sample was chosen at the failure boundary, so this is an upper bound on outcome disagreement |
| Videos | decode every MP4 from the download; compare to `videos.json` | 10/10 decode, hashes and frame counts match the index; every sidecar's single-environment replay outcome equals its evaluation record |
| Public availability | anonymous `curl -L` of `report.pdf`, `deck.pdf`, `SHA256SUMS`, `checkpoints-combined-seed11.tar.gz` | HTTP 200; anonymously downloaded `SHA256SUMS` identical to the packaged file |

Final URLs:
- Release: https://github.com/ywen0511/CSCI645-Project/releases/tag/v2.0.0
- Experiment source: https://github.com/ywen0511/CSCI645-Project/tree/experiment-v2
- Release source: https://github.com/ywen0511/CSCI645-Project/tree/v2.0.0
- Branch: https://github.com/ywen0511/CSCI645-Project/tree/study/v2-diagnostics
