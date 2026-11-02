# Decision log

## Initial handoff: 2026-11-02

Owner-confirmed requirements:

- Approximately one month remains; exact deadline and remote hardware are not specified.
- Execution will happen remotely. The remote agent must understand the entire assignment from GitHub alone.
- Use Isaac Sim through Isaac Lab, two parallel-jaw grippers, geometric coordination, and bounded position-residual PPO.
- Complete implementation, experiments, reporting, and uploads, including checkpoints and a final GitHub Release.
- All project content is in English. The original proposal must remain unchanged.

Engineering defaults selected for a concrete starting point:

- Two Franka arms and one rectangular object; score only the handover, beginning from a physically established giver grasp.
- Three receiver position residuals, fixed orientation targets, one policy; no dexterous fingers or multi-agent RL.
- Direct single-agent external Isaac Lab project, existing IK/PPO integrations, fixed PhysX backend.
- Primary spatial perturbations are translations; coupled giver/object start displacement preserves a feasible initial grasp.
- Three seeds, five methods including the phase-input ablation, nine final evaluation conditions, and the budgets in `configs/protocol.json`.
- Explicit phase-label masking retains raw contact observations and network dimensionality. It does not remove geometry's contact information.

These are proposed implementation choices, not completed experiments. The remote agent may calibrate documented pilot parameters before the protocol freeze while preserving the scientific scope. No simulation, policy training, or GPU timing has been performed by this handoff.

## Entries to add during execution

For each material decision, record date, decision, evidence, affected files/configs, whether made before or after protocol freeze, and implications for comparability. Especially record version pair/backend, frame convention, scene dimensions, thresholds/rewards, perturbation feasibility, training budget/batch size, checkpoint selection, deviations, failure corrections, and release verification.

Use explicit facts and links to run IDs/logs. Do not retroactively rewrite pilot choices as preregistered facts or delete unsuccessful runs from the history.
