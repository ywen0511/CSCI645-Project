# Pilot / development evidence (not held-out results)

Calibration runs made **before the protocol freeze** on development cases (seed 6452028) and pilot seeds.
They justify the decisions in `docs/DECISIONS.md` and must not be read as final results.

| Path | Content |
|---|---|
| `inspect_scene_v2.json` | Asset bodies/joints, sensor matching, finger geometry, IK seeds (horizontal grasp) |
| `scripted1/summary.json` | First clean nominal episodes |
| `gate1b/`, `gate1c/` | Gate-1 batches before/after the horizontal-grasp change (clean 100, negative controls, dev suites) |
| `negtable2/` | Table-support negative control (narrow table) |
| `gate2/` | Development suite with the final geometry bound (1 cm) |
| `pilot_*_s101/` | 5M-transition pilot PPO runs (checkpoint ledger, development evaluation of every checkpoint) |
| `smoke_ppo1024/` | Training/resume/replay smoke test |

Full pilot logs (including training scalars) are in the release `logs.tar.gz`.
