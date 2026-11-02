# Execution runbook and acceptance gates

The owner allocated approximately one month. The week labels are planning guidance, not known calendar deadlines. Advance by verified gates. Keep implementing and debugging until the full project and release are finished or a specific external blocker prevents progress.

## Gate 0: remote preflight

- Record hardware, version compatibility, asset availability, GitHub capabilities, storage, and expected compute allocation.
- Run official simulation/control and short RL examples.
- Commit exact setup instructions and dependency/version lock information.
- Update status with observed facts and links to logs; no experimental success claims yet.

## Gate 1: scripted baseline (target: week 1)

- Implement a valid physically held start, receiver approach/close, fixed-time giver release, retreat, and independent holding evaluation.
- Inspect one full episode, including reset and actual contact/force traces.
- Run 20 development resets, then 100 clean development episodes. Aim for at least 95% valid clean handover success to establish a meaningful nominal controller. This is a development gate, not a claimed final test result. If lower, diagnose contact/control/reset before adding learning; record any justified gate revision.
- Run batched environments and partial resets without cross-environment state leakage or NaN/Inf.
- Verify negative controls: giver opens without receiver -> no success; giver keeps supporting -> no success; object rests on table -> no success.
- Commit baseline, example video, raw outcomes, and any unresolved limitations. A deterministic clean scene may produce identical repeats; say so.

## Gate 2: geometry and perturbations (target: week 2)

- Implement the same geometry module for geometry-only and combined modes.
- Verify delayed release only after the scheduled request and only while the wait limit permits.
- Confirm spatial perturbations persist after reset and remain reachable with fixed orientations.
- Run development-only spatial, early/late timing, and joint cases for nominal and geometry.
- Inspect representative failures, not only successes. Check target saturation and motion conflicts.
- Implement case-suite generation, raw episode records, summary analysis, and independent evaluator tests.

## Gate 3: learning path and freeze (target: week 2/3)

- Implement bounded residual PPO, observations/rewards, contact-phase masking, validation, checkpointing, resume, and exact run provenance.
- Demonstrate finite short-run learning updates and save/load behavior; a reward increase alone does not prove handover success.
- Run pilot calibration within its aggregate budget. Check for reward exploitation and loss of residual authority under geometry.
- Benchmark throughput and storage. Choose final common budget and batch size based on evidence; keep three seeds and all required methods.
- Freeze full resolved protocol, source SHA/tag, case lists and hashes, threshold definitions, and selection rule before final runs.

## Gate 4: complete experiments (target: week 3/4)

- Finish all nine learned-policy runs with matched transition budgets, periodic validation, and selected/final checkpoints.
- Complete the full final evaluation matrix using the shared held-out suite.
- Reconcile scheduled cases, valid cases, invalid resets, failures, duplicate checks, and infrastructure errors.
- Produce per-seed and aggregate metrics, uncertainty, learning curves, collision/completion-time results, and diagnostic failure analysis.
- Preserve unsuccessful methods and negative findings. Do not rerun only unfavorable test cases until they pass.

## Gate 5: documentation and artifact verification (target: week 4)

- Produce final Markdown/PDF report, figures, raw data/log archives, checkpoint index, representative videos, and video index.
- Include measured resource use, limitations, exact methods, statistical units, software reuse, and actual AI assistance.
- Verify report numbers against generated summaries; visually inspect plots and rendered PDF.
- Pass clean-clone install and separate-process checkpoint replay checks.
- Package release assets, run artifact validation, upload to a draft release, download again, verify checksums and replay, then publish final release.
- Update README and `STATUS.json` with actual results and URLs. Confirm the final remote branch/tag/release state.

## Progress ledger

For each run store run ID, method, seed, type (smoke/pilot/final), requested/actual transitions, state (queued/running/failed/resumed/completed), source and config hashes, checkpoint paths/hashes, start/end UTC, hardware, wall time, log links, and any exception. Keep a small committed index; archive verbose logs in releases.

On interruption, stop safely, save supported training state, record the last completed milestone and exact resume command, and push current source/status when possible. Resume from the ledger rather than retraining blindly. Automatic continuation must not create duplicate evaluation records.

## What does not count as completion

- A specification, code scaffold, successful imports, or CPU unit tests alone.
- A simulator opening or a random policy producing a video.
- A training job still running in the background without collected outputs.
- A single favorable seed or only a combined-method demo.
- A release with only source code and no checkpoints/raw evaluation evidence.
- Locally saved artifacts without verified downloadable release assets.
- A claimed improvement unsupported by the full matched evaluation.

If resources or credentials make a requirement impossible, keep the completion flags false, identify the missing deliverable, preserve all completed work, and provide a precise handoff. Do not conceal the shortfall behind a final-looking release title.
