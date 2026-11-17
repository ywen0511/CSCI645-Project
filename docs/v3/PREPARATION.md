# V3 preparation evidence and handoff boundary

Preparation started 2026-11-06 from v2 closeout commit
`4204da23b17f920d955a0bc90f94a8df271c524f` and completed on 2026-11-07.
The preparer used an isolated macOS CPU-test environment (Python 3.11, torch 2.15.0,
NumPy 2.4.6, pytest 9.2.0). This differs from the simulator's locked environment.
No Isaac Sim, Isaac Lab application, CUDA/MPS workload, PPO training, simulator
evaluation, video rendering or checkpoint generation was run during preparation.

Implemented and CPU checked:

- Case/frame-deterministic sensor noise, constant bias, causal delay, EMA,
  startup/reset behavior, partial-reset isolation and repeated-read idempotence.
- Five-frame history with chronological order and independent reset padding.
- Optional simulator integration for estimated translation/velocity, geometry
  alignment/gating, giver-reference inference, history/repeated-current/permuted
  history; truth remains in independent evaluation and training reward.
- Draft five-profile design (23 training seeds/runs), 312 development and 240
  validation cases, six development matrices (28,080 logical episodes).
- Hash-aware v3 evaluation reuse, malformed/missing/duplicate-case rejection,
  strict formal index completeness and resume metadata checks.
- Paired seed/base-case-cluster bootstrap with deterministic baseline handling;
  complete raw-to-table analysis exercised with temporary synthetic fixtures.
- Default configuration hash compatibility with disabled v3 fields.

Verification commands:

```bash
CUDA_VISIBLE_DEVICES='' python -m pytest -q
python -m compileall -q src scripts
python scripts/v3_prepare.py
git diff --check
```

The exact CPU test counts, runtime versions and command exit codes are in
[`../../results/v3/preparation_cpu.json`](../../results/v3/preparation_cpu.json).
The only simulator registration test is skipped because Isaac Lab is not installed.
Synthetic analysis fixtures exist only in temporary test directories and are not
project results. Development/validation suite hashes are in
[`../../configs/v3/SUITES.json`](../../configs/v3/SUITES.json).

The final suite has not been generated, no protocol freeze has been declared, no
formal run has completed and no scientific v3 result/checkpoint/release exists.
`V3_STATUS.json` records these pending items explicitly.

The remote agent must validate control-loop/reset timing, actual contact dynamics,
CUDA batch behavior, normalization/checkpoint compatibility, no hidden translation
leakage, zero-residual equivalence, and physical outcome integrity. CPU tests and
syntax compilation do not establish those properties in the simulator. Correct
integration if needed before protocol freeze, following `V3_EXECUTION.md`.

Remaining remote engineering includes orchestration/job manifests, baseline
selection, frozen final matrices, trace/plot/report/deck generation, packaging and
fresh-download verification. The assignment specifies all required outputs and
acceptance gates. Optional physical-transfer spawn overrides are not implemented
here and must not be claimed as validated by changing a task-level size field.
