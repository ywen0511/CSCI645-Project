# Release verification record

Release: [v1.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v1.0.0), published
2026-11-03 05:21 UTC. The release tag `v1.0.0` points to commit `8287646` (analysis, report and packaging).
Experiment source: tag `experiment-v1`, commit `7a64505`. This record and the final README/STATUS update
were added in a later delivery-index commit; they are not part of the tagged release commit.

| Check | Result |
|---|---|
| Local packaging validation (`scripts/verify_release.py`) | 20 artifacts: sizes, hashes and 9/9 method-seed checkpoint archives OK |
| Private paths in assets | 0 occurrences of the cluster work or home path in any archive member or index file (redacted at packaging) |
| Draft upload | 22 assets, 76.9 MB |
| Fresh download (`gh release download` into an empty folder) | 22 files; `sha256sum -c SHA256SUMS`: 21/21 OK (manifest + 20 artifacts); `verify_release.py` from a clean clone: OK |
| Archive semantics | 556 archive members re-hashed against `archive_inventories.json`: 0 mismatches. Each checkpoint archive holds 11 periodic checkpoints plus `final.pt` and `latest.pt` (resume), the ledger, the run metadata and `checkpoint_metadata.json` |
| Figures and tables regenerated from downloaded raw records | `build_run_index.py` + `analyze.py` on the extracted `results/`: `tables.md`, `counts.csv`, `metrics_per_run.csv`, `metrics_per_method.csv`, `comparisons.csv`, `failure_breakdown.csv` and `learning_curves.csv` are byte-identical to the committed `results/summary/{primary,secondary}` |
| Count reconciliation | 19,800 scheduled = 19,800 recorded; 0 duplicates, 0 invalid resets, 0 infrastructure errors |
| Clean-clone reproduction (fresh `git clone`, `experiment-v1`, documented environment) | one nominal clean episode: success; one geometry `final-joint_early_stress-0000` episode: success |
| Separate-process replay of downloaded checkpoints (one per learned method + one final checkpoint), 20 predefined final cases each (`position_stress` 0000-0019) | checkpoint SHA-256 equal to the archived records for all 4; same terminal reason as the archived evaluation in **79/80** cases (`combined_seed11` selected 20/20, `combined_no_phase_seed11` selected 20/20, `combined_seed11` final 20/20, `residual_seed33` selected 19/20). The one difference is a stress case near the palm-contact boundary; the replay batch (20 envs) differs from the evaluation batch (900 envs), and batched GPU PhysX is not bitwise reproducible across batch compositions |
| Videos | all 10 MP4 files from the download decode, frame counts equal their sidecars; the single-environment replay outcome of every video equals its archived evaluation record (10/10) |
| Report | `report.pdf` (12 pages) rendered and visually checked; numbers taken from the generated summaries |
| Public availability | anonymous `curl` of `report.pdf`, `SHA256SUMS` and a checkpoint archive: HTTP 200; the anonymously downloaded `SHA256SUMS` is identical to the packaged file |
