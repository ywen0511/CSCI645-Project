# Complete remote-agent assignment

> Historical v1 assignment. On branch `study/v3-observation-robustness`, the active
> self-contained assignment is [`../POST_V3_EXECUTION.md`](../POST_V3_EXECUTION.md).
> Preserve this document as history; do not restart v1 or mark v3 complete from v2 status.

You are working for Yan Wen on the CSCI 645 Fall 2026 final project in `https://github.com/ywen0511/CSCI645-Project`. Complete the project end to end using this repository alone for assignment context. All output must be English. The owner has approximately one month and expects implementation and experimental execution on your remote machine, with all deliverables uploaded to this repository and GitHub Releases.

Read `AGENTS.md`, `README.md`, the proposal, `docs/PROJECT_SPEC.md`, `docs/IMPLEMENTATION.md`, `docs/ENVIRONMENT.md`, `docs/EXPERIMENTS.md`, `docs/RUNBOOK.md`, and `docs/RELEASE.md`. The proposal is included in the repository; do not request access to the owner's desktop or previous chat.

## Research task

Implement simulated handover between two Franka arms with two-finger parallel-jaw grippers. A giver holds one rigid object; a receiver grasps another region and takes over support. Build a fixed nominal trajectory/gripper controller, an untrained geometric coordination and release-gating module, and a bounded position-residual PPO policy. Keep commanded orientations fixed. Compare nominal, geometry, residual, combined, and combined without the explicit contact-phase observation.

Use Isaac Sim through Isaac Lab with a consistent physics backend. Use low-dimensional simulator state and physical contact-based holding. Do not attach the object with a hidden weld or substitute a pretrained dexterous-hand task. Train online in simulation; external demonstrations are not required.

## Execute, do not only plan

1. Inventory the remote GPU/software and GitHub permissions; pin compatible versions and verify official simulation/control and training examples.
2. Create the external task package, reset logic, scripted controller, independent success/failure evaluator, and telemetry. Verify one environment, repeated resets, and parallel environments.
3. Calibrate a reliable no-perturbation baseline and physically feasible perturbations using development-only cases. Implement geometry and demonstrate its behavior without learning.
4. Implement residual composition, observations, shared rewards, PPO integration, checkpointing, resume, and phase-input ablation.
5. Freeze configuration and evaluation suites before final training. Run the required seeds and equal training budgets. Select checkpoints using validation only.
6. Run all evaluation conditions, produce uncertainty summaries, learning curves, failure analysis, and representative videos. Preserve raw episode records and provenance.
7. Write the final English report with actual methods, results, limitations, references, and software/AI-assistance disclosure. Render and visually check its PDF.
8. Publish source/configuration, all required checkpoints and results, checksums, replay instructions, and a final GitHub Release. Download the release afresh and verify it. Do not mark completion until this succeeds.

You are authorized to make and push project changes and publish these deliverables using available credentials. Resolve routine implementation problems autonomously. Do not ask for permission at each milestone. Do not spend money or change repository visibility/account security without separate authorization.

## First progress update

Report GPU model/VRAM, OS/driver, selected simulator and Lab versions, physics backend, working example commands, GitHub read/write/release capability, and the first milestone being implemented. Treat any initial protocol numbers as pilot defaults until validated. Update `STATUS.json` after each milestone and record decisions in `docs/DECISIONS.md`.

## Final response

Provide links to the final release, immutable experiment-source tag, report, evaluation summary, checkpoint index, and video index. State which acceptance checks actually passed. If a hard external blocker remains, publish the completed work where authorized and give a precise incomplete-status report. A plan, scaffold, test-only pass, or uploaded random policy is not completion.
