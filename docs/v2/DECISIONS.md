# v2 decision log

UTC timestamps. Evidence paths are relative to the repository unless marked as cluster paths.
The v1 log ([docs/DECISIONS.md](../DECISIONS.md)) is historical and unchanged.

### 2026-11-04 — Start of the follow-up

- Work branch `study/v2-diagnostics` created from `impl/handover` @ `a3bb983` (the follow-up README).
  No earlier follow-up work existed on the remote (only `main`, `impl/handover`; tags `experiment-v1`, `v1.0.0`).
- `STATUS.json` restructured: `v1_completed: true` plus a separate `followup` block.
- Compute: `dgx047` (8x A100-40GB, LSF `gpu_large_shared`) was idle at start; v1 also ran there. All GPU
  work uses self-terminating 1-GPU jobs; no reservation is held between jobs.
- Environment: reuse the v1 isolated conda environment (Isaac Lab v3.0.0, Isaac Sim 6.2.0.0, RSL-RL 5.5.1);
  no upgrades, so archived v1 checkpoints and the v1 physics configuration stay valid.
