# Agent instructions

## Active continuation assignment

The V3 study is completed and published as `v3.0.0`; `V3_EXECUTION.md` is historical.
On `study/v4-grasp-uncertainty`, the active self-contained remaining-work assignment
is `V4_REMAINING.md`, tracked in `POST_V3_STATUS.json`. Stage A is already verified
and published as v3.0.1; the original contract remains `POST_V3_EXECUTION.md`. It supersedes
historical runbooks for new work. Preserve `V3_STATUS.json`, frozen inputs, published
evidence, tags and releases. Do not restart the original V3 training matrix.
The local preparation agent performs CPU-only maintenance; no GPU or simulator runs.
The remote execution agent performs the documented verification and the separate
uncertain-grasp extension on already available resources. All public content is English.

## Mission and authorization

The owner, GitHub user `ywen0511`, explicitly requested a self-contained repository that a remote agent can read and use to complete the entire project, including implementation, training, evaluation, checkpoints, reports, videos, and GitHub Releases. All repository content and deliverables must be in English.

Work in `ywen0511/CSCI645-Project`. Read `V4_REMAINING.md` and its linked specifications before implementing. Continue through the complete runbook; do not stop after generating a scaffold, passing unit tests, running one episode, or starting a background training job.

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

Active continuation completion means all remaining-work acceptance gates in `V4_REMAINING.md` and the preserved scientific contract pass. Historical v1/v2 gates in `docs/RUNBOOK.md` and `docs/RELEASE.md` remain references. Confirm a clean-clone installation, checkpoint replay, downloaded artifact checksums, and accessible published release URLs. Final communication must link the source commit/tag, release, report, summary metrics, checkpoints, and videos, and identify any unfulfilled requirement.
