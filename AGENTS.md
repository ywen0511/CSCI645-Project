# Agent instructions

## Active continuation assignment

V3 and V4 are complete and released. The final review assignment
`FINAL_DELIVERY_HANDOFF.md` is **complete**: supplement release v4.0.2 is published and
publicly verified (`FINAL_REVIEW_STATUS.json`, `docs/final_review/PUBLIC_VERIFICATION.md`).
There is no active assignment. `V4_REMAINING.md`, `POST_V3_EXECUTION.md` and `V3_EXECUTION.md`
are historical contracts. Preserve historical status files, frozen inputs, published evidence,
tags and releases. Do not restart completed training or evaluation matrices. All public
content is English.

## Mission and authorization

The owner, GitHub user `ywen0511`, explicitly requested a self-contained repository that a remote agent can read and use to complete the entire project, including implementation, training, evaluation, checkpoints, reports, videos, and GitHub Releases. All repository content and deliverables must be in English.

Work in `ywen0511/CSCI645-Project`. Read `FINAL_DELIVERY_HANDOFF.md` before implementing. Complete its publication and verification gates; do not stop at a local package or draft release. The broader historical mission below does not override the current CPU-only scope.

Authorized actions within available resources include implementing and fixing code, installing compatible project dependencies in an isolated environment, running simulations and experiments, resuming failed runs, committing and pushing project changes, creating project tags, and uploading/publishing project results in GitHub Releases. Routine engineering decisions and these uploads do not need repeated confirmation. Do not provision paid resources, change account/security settings, erase unrelated data, force-push shared history, or overwrite an existing published release. External compute must already be available or separately authorized.

## Working rules

- Preserve the original proposal PDF and its extracted text. They document the submitted plan, not current completion status.
- Treat `docs/PROJECT_SPEC.md` and `docs/EXPERIMENTS.md` as the scientific contract. `configs/protocol.json` contains initial defaults to calibrate and freeze, not guaranteed optimal values.
- The owner chose Isaac Sim using Isaac Lab and parallel-jaw grippers. Do not silently switch to MuJoCo, Isaac Gym, dexterous hands, vision, or a different research question.
- Implement an external Isaac Lab project; keep project code outside the upstream simulator repository. Prefer Direct single-agent for explicit per-environment phase logic unless a documented engineering reason favors a manager-based implementation.
- Keep state, reset, phase, and timers independent for every parallel environment. Never use one global episode phase for a batch.
- Read the installed version's API and examples before using them. Lock versions, backend, coordinate frames, quaternion convention, and controller semantics.
- Keep source, configuration, and small summaries in Git. Put large checkpoints/logs/videos in release assets. Never commit credentials, private absolute paths, or simulator redistributions without permission.
- Do not fabricate metrics, successful execution, plots, checkpoints, or completion claims. Label smoke, pilot, validation, final, failed, and resumed runs distinctly.
- Never select checkpoints, hyperparameters, thresholds, or videos to conceal unfavorable held-out results. Report limitations and negative findings.
- Use the same evaluator, physical parameters, randomization realizations, and outcome definitions for every method.
- Make incremental commits and push meaningful milestones. Before long runs, commit the executable source and record its SHA in run metadata. Record any dirty diff explicitly; final experiments must use clean committed source.
- Maintain `STATUS.json`, `docs/DECISIONS.md`, and a run index. On interruption, persist enough state to resume without the owner reconstructing the conversation.
- Do not run simulator training on ordinary GitHub-hosted CI. CPU checks can validate pure logic and artifact integrity; they cannot prove contact dynamics or policy performance.
- Use the existing training library for PPO rather than implementing a new optimizer. Test task semantics and scientific invariants, not just duplicated implementation details.

## Autonomy and escalation

Choose reasonable engineering defaults, investigate failures, and continue independent work. An unavailable compatible GPU, missing required asset access, unavailable GitHub write credentials, or an actual irreconcilable scientific-scope change is a concrete blocker. Record evidence and the exact missing capability rather than silently replacing the task or marking it done. Lack of statistical improvement is not a blocker.

The one-month planning horizon is not permission to launch unbounded jobs. Use the pilot and frozen budgets in `docs/EXPERIMENTS.md`; estimate throughput before full runs. Never silently reduce the final evidence requirements. Document incomplete evidence if resources make completion impossible.

## Completion

Active completion means every gate in `FINAL_DELIVERY_HANDOFF.md` passes. Historical study gates and GPU verification are already recorded; do not rerun them as part of the CPU supplement. Verify new release downloads and inherited artifact checksums/availability. Final communication must link the source commit/tag, release, report, summary metrics, checkpoints, videos and public verification, and identify any unfulfilled requirement.
