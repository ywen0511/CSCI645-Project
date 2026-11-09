# CSCI 645 — Robust bimanual handover

**V3 is completed and published. The active continuation assignment is
[POST_V3_EXECUTION.md](POST_V3_EXECUTION.md).** A remote agent should read that file
and execute it through verification and publication; no previous chat or local
files are needed. It covers the reproduction repairs and a new, separately frozen
study of uncertain giver grasp geometry. Do not restart the archived V3 assignment.

This project uses Isaac Sim through Isaac Lab, PhysX, two Franka arms with
**two-finger parallel-jaw grippers**, fixed commanded orientations, and a bounded
XYZ PPO residual added to geometric coordination. Training data come from simulator
interaction; no external demonstration dataset is required.

## Completed V3 evidence

- [Published V3 release: results, checkpoints, PDFs, slides and videos](https://github.com/ywen0511/CSCI645-Project/releases/tag/v3.0.0)
- [English report](report/v3/report.md), [results](results/v3/summary/family_condition_summary.json),
  [verification record](docs/v3/VERIFICATION.md), [archived completion status](V3_STATUS.json).
- Immutable experiment source: `experiment-v3`, commit
  `3811f5da5ef55638f95f7306e449609877f546df`.
- 23 formal training runs; 13 final conditions with 200 paired cases each;
  130,000 executed final episodes (135,200 logical episodes including baseline aliases).
- 30 release assets include the checkpoint index, all saved checkpoints, raw records,
  source snapshots, checksums, a 19-page report, 15-slide deck, and 8 clips plus a montage.

The selected combined policies and strongest geometric baseline both achieve
100% on the frozen final suite. This is a ceiling result, **not evidence that PPO
improves on geometry or that the methods are generally equivalent**. The accurate
giver reference and known grasp transform explain an important limitation; final
history-policy checkpoints also expose training instability. Physical transfer
experiments were not performed in V3. The continuation tests uncertain grasp geometry
with fair, equally informed baselines and reports negative results if they persist.

## Reproduce or continue

[Reproduction instructions](docs/v3/REPRODUCE.md) separate the immutable experiment,
archived delivery, and repaired tooling checkouts. They include CPU table regeneration,
non-mutating suite reconstruction, a complete 65-case replay, and checkpoint resume.
The old `v3_prepare.py --final` is a historical creation command, not the rebuild command.

```bash
git clone --branch study/v3-observation-robustness https://github.com/ywen0511/CSCI645-Project.git
cd CSCI645-Project
cat POST_V3_EXECUTION.md
```

For CPU regression checks in an isolated environment with torch, numpy and pytest:

```bash
CUDA_VISIBLE_DEVICES='' python -m pytest -q
```

The maintenance repairs passed remote GPU acceptance on 2026-11-09 (sections 1–4 of the
reproduction instructions executed verbatim; 455/455 replay, 52/52 reload, resume, byte-identical
suites and tables; see [maintenance notes](docs/v3/MAINTENANCE.md)). They are published as the
maintenance release [v3.0.1](https://github.com/ywen0511/CSCI645-Project/releases/tag/v3.0.1), which
keeps every v3.0.0 asset byte-identical. Track the continuation in
[POST_V3_STATUS.json](POST_V3_STATUS.json); the V4 uncertain-grasp study is developed on branch
`study/v4-grasp-uncertainty`. CPU tests do not validate contact physics.

## History

- [Original proposal](proposal/proposal.txt), preserved as submitted.
- [V2 release](https://github.com/ywen0511/CSCI645-Project/releases/tag/v2.1.1),
  [V2 report](report/v2/report.md), [historical V2 README](README_V2_CLOSEOUT.md).
- [Archived V3 execution contract](V3_EXECUTION.md). Its completion flags describe
  the published V3 study, not the active continuation.

Preserve all existing experiment tags, published releases, raw evidence and source
history. Publish new work under new tags; never overwrite previous release assets.
