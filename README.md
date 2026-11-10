# CSCI 645 — Robust bimanual handover

**V4 (uncertain giver grasp) is released as [v4.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.0)**
on branch `study/v4-grasp-uncertainty`: [report](report/v4/report.md) (PDF in the release),
[slides](report/v4/slides.pptx), [summary metrics](results/v4/summary/family_condition_summary.json),
[paired effects](results/v4/summary/paired_effects.json), [reproduction](docs/v4/REPRODUCE.md),
[verification](docs/v4/VERIFICATION.md), [decision log](docs/v4/DECISIONS.md), [status](POST_V3_STATUS.json).
Simulator source of every formal run: tag `experiment-v4`. V3 and its maintenance release v3.0.1 are complete.
The remote assignment that produced V4 is [V4_REMAINING.md](V4_REMAINING.md) (contract: [POST_V3_EXECUTION.md](POST_V3_EXECUTION.md)).

**V4 in one paragraph.** When the bar's position inside the giver's grasp is unknown (physically produced, up to
+15 mm along the bar), the V3 fixed-transform grasp reference fails beyond about +5 mm (5.5% success at +15 mm); a
0.5 s calibration from the same noisy sensor restores it (94.5%). Residual PPO with or without a four-frame history
adds at most a few in-distribution cases (primary contrasts touch zero) and is fragile outside its training support.

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
git clone --branch study/v4-grasp-uncertainty https://github.com/ywen0511/CSCI645-Project.git
cd CSCI645-Project
cat V4_REMAINING.md
```

For CPU regression checks in an isolated environment with torch, numpy and pytest:

```bash
CUDA_VISIBLE_DEVICES='' python -m pytest -q
```

The maintenance repairs passed remote GPU acceptance on 2026-11-09 (sections 1–4 of the
reproduction instructions executed verbatim; 455/455 replay, 52/52 reload, resume, byte-identical
suites, 34/35 byte-identical tables plus one numerically equal table; see [maintenance notes](docs/v3/MAINTENANCE.md)). They are published as the
maintenance release [v3.0.1](https://github.com/ywen0511/CSCI645-Project/releases/tag/v3.0.1), which
keeps every v3.0.0 asset byte-identical. Track the continuation in
[POST_V3_STATUS.json](POST_V3_STATUS.json); the V4 uncertain-grasp study is developed on branch
`study/v4-grasp-uncertainty`. CPU tests do not validate contact physics.

## V4 progress and evidence boundary

The implementation, two development rounds and baseline selection are present. The
uploaded A1–A9 acceptance checks and five-profile smoke resume pass; see
[acceptance](results/v4/acceptance/acceptance.json) and its
[mixed-commit provenance](results/v4/acceptance/PROVENANCE.json). Pilot execution is
reported in the decision log, but a completed pilot summary is not yet committed.
The public snapshot has no formal freeze, experiment-v4 tag, formal results or V4 release.

Development data show the historical fixed-transform geometry fails on uncertain grasps
(7/24 and 3/24 successes in the 10 mm and 15 mm conditions), while calibrated and EMA
geometry each reach 24/24 in those conditions and mixed ID. Mixed OOD remains imperfect:
22/24 for calibrated geometry and 23/24 for EMA. These are **development observations**,
not held-out comparisons or evidence of PPO improvement. See
[development results](results/v4/development/round2_summary.json).

[CPU workflow review](docs/v4/CPU_REVIEW.md) explains the local repairs and validation.
The local preparation agent runs no GPU or simulator work. The freeze preflight command
`python scripts/v4_freeze.py check` intentionally refuses readiness until genuine pilot
evidence is committed. It does not create a freeze or launch a simulator.

## History

- [Original proposal](proposal/proposal.txt), preserved as submitted.
- [V2 release](https://github.com/ywen0511/CSCI645-Project/releases/tag/v2.1.1),
  [V2 report](report/v2/report.md), [historical V2 README](README_V2_CLOSEOUT.md).
- [Archived V3 execution contract](V3_EXECUTION.md). Its completion flags describe
  the published V3 study, not the active continuation.

Preserve all existing experiment tags, published releases, raw evidence and source
history. Publish new work under new tags; never overwrite previous release assets.
